#!/usr/bin/env python3
"""
Bot de Criptomoedas SIMPLIFICADO - Garantido para funcionar no Render
"""

import os
import time
import logging
from datetime import datetime
import requests
import json

# Configuração simples de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleCryptoBot:
    def __init__(self):
        # Configurações via variáveis de ambiente
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.chat_id = os.getenv('CHAT_ID')
        
        if not self.telegram_token or not self.chat_id:
            logger.error("TELEGRAM_TOKEN e CHAT_ID são obrigatórios!")
            raise ValueError("Configurações não encontradas")
        
        # Configurações do bot
        self.config = {
            'pairs': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT'],
            'check_interval': 300,  # 5 minutos
            'rsi_oversold': 30,
            'rsi_overbought': 70
        }
        
        # Cache para evitar spam
        self.last_alerts = {}
    
    def get_price_data(self, symbol):
        """Obtém dados de preço da Binance API pública"""
        try:
            # API pública da Binance - sem limite de rate
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'symbol': symbol,
                    'price': float(data['lastPrice']),
                    'change_24h': float(data['priceChangePercent']),
                    'volume': float(data['volume'])
                }
            else:
                logger.warning(f"Erro na API para {symbol}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao obter dados de {symbol}: {e}")
            return None
    
    def calculate_simple_rsi(self, symbol):
        """Calcula RSI simples baseado na variação 24h"""
        try:
            data = self.get_price_data(symbol)
            if not data:
                return None
            
            # RSI simplificado baseado na variação 24h
            change = data['change_24h']
            
            # Mapeia variação para RSI aproximado
            if change <= -10:
                rsi = 15  # Muito oversold
            elif change <= -5:
                rsi = 25  # Oversold
            elif change <= -2:
                rsi = 35  # Baixo
            elif change >= 10:
                rsi = 85  # Muito overbought
            elif change >= 5:
                rsi = 75  # Overbought
            elif change >= 2:
                rsi = 65  # Alto
            else:
                rsi = 50  # Neutro
            
            return {
                'symbol': data['symbol'],
                'price': data['price'],
                'change_24h': change,
                'rsi': rsi,
                'volume': data['volume']
            }
            
        except Exception as e:
            logger.error(f"Erro ao calcular RSI para {symbol}: {e}")
            return None
    
    def analyze_signals(self, data):
        """Analisa sinais de trading"""
        signals = []
        
        if not data:
            return signals
        
        rsi = data['rsi']
        change = data['change_24h']
        
        # Sinais baseados no RSI
        if rsi <= self.config['rsi_oversold']:
            signals.append(f"🟢 RSI Oversold ({rsi:.0f}) - Possível compra")
        elif rsi >= self.config['rsi_overbought']:
            signals.append(f"🔴 RSI Overbought ({rsi:.0f}) - Possível venda")
        
        # Sinais baseados na variação 24h
        if change <= -10:
            signals.append(f"🟢 Queda forte (-{abs(change):.1f}%) - Oportunidade de compra")
        elif change >= 10:
            signals.append(f"🔴 Alta forte (+{change:.1f}%) - Considere venda")
        
        # Volume alto (indicador de interesse)
        if data['volume'] > 100000:
            signals.append(f"📊 Volume alto - Interesse do mercado")
        
        return signals
    
    def format_alert(self, data, signals):
        """Formata mensagem de alerta"""
        try:
            symbol_clean = data['symbol'].replace('USDT', '/USDT')
            
            message = f"🚨 *ALERTA - {symbol_clean}* 🚨\n\n"
            message += f"💰 *Preço:* ${data['price']:,.4f}\n"
            message += f"📈 *24h:* {data['change_24h']:+.2f}%\n"
            message += f"📊 *RSI:* {data['rsi']:.0f}\n"
            
            if signals:
                message += "\n🎯 *Sinais:*\n"
                for signal in signals:
                    message += f"• {signal}\n"
            
            # Links
            message += f"\n🔗 [Binance](https://www.binance.com/en/trade/{data['symbol']})\n"
            message += f"⏰ {datetime.now().strftime('%d/%m %H:%M')}"
            
            return message
            
        except Exception as e:
            logger.error(f"Erro ao formatar mensagem: {e}")
            return f"Erro ao formatar alerta para {data['symbol']}"
    
    def send_telegram_message(self, message):
        """Envia mensagem via Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("Mensagem enviada com sucesso")
                return True
            else:
                logger.error(f"Erro ao enviar mensagem: {response.status_code}")
                # Tenta sem formatação
                payload['parse_mode'] = None
                payload['text'] = message.replace('*', '').replace('_', '')
                response = requests.post(url, json=payload, timeout=10)
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Erro no envio: {e}")
            return False
    
    def should_send_alert(self, symbol):
        """Verifica se deve enviar alerta (anti-spam)"""
        current_time = time.time()
        
        if symbol in self.last_alerts:
            # 30 minutos de cooldown
            if current_time - self.last_alerts[symbol] < 1800:
                return False
        
        self.last_alerts[symbol] = current_time
        return True
    
    def monitor_pair(self, symbol):
        """Monitora um par específico"""
        try:
            logger.info(f"Monitorando {symbol}...")
            
            # Obtém dados e calcula indicadores
            data = self.calculate_simple_rsi(symbol)
            
            if not data:
                logger.warning(f"Sem dados para {symbol}")
                return
            
            # Analisa sinais
            signals = self.analyze_signals(data)
            
            # Envia alerta se necessário
            if signals and self.should_send_alert(symbol):
                message = self.format_alert(data, signals)
                success = self.send_telegram_message(message)
                
                if success:
                    logger.info(f"Alerta enviado para {symbol}: {len(signals)} sinais")
                else:
                    logger.error(f"Falha ao enviar alerta para {symbol}")
            else:
                logger.info(f"{symbol}: Sem sinais ou em cooldown")
                
        except Exception as e:
            logger.error(f"Erro ao monitorar {symbol}: {e}")
    
    def run_monitoring_cycle(self):
        """Executa um ciclo de monitoramento"""
        logger.info("=== Iniciando ciclo de monitoramento ===")
        
        for symbol in self.config['pairs']:
            try:
                self.monitor_pair(symbol)
                time.sleep(2)  # Pausa entre pares
            except Exception as e:
                logger.error(f"Erro no monitoramento de {symbol}: {e}")
        
        logger.info("=== Ciclo concluído ===")
    
    def start_monitoring(self):
        """Inicia monitoramento contínuo"""
        logger.info("🤖 Iniciando bot simplificado...")
        
        # Teste inicial
        try:
            test_data = self.get_price_data('BTCUSDT')
            if test_data:
                logger.info(f"✅ Conexão OK - BTC: ${test_data['price']:,.2f}")
            else:
                raise Exception("Falha no teste de conexão")
        except Exception as e:
            logger.error(f"❌ Falha na inicialização: {e}")
            return
        
        # Mensagem de inicialização
        init_message = f"""
🤖 *Bot Crypto Simplificado Iniciado*

📊 *Monitorando:* {len(self.config['pairs'])} pares
⏱️ *Intervalo:* {self.config['check_interval']}s
📈 *RSI Limites:* {self.config['rsi_oversold']}-{self.config['rsi_overbought']}

🎯 *Pares:*
• BTC/USDT, ETH/USDT
• BNB/USDT, SOL/USDT  
• ADA/USDT

Bot ativo! 🚀
        """
        
        self.send_telegram_message(init_message.strip())
        
        # Loop principal
        while True:
            try:
                start_time = time.time()
                self.run_monitoring_cycle()
                
                # Calcula tempo de espera
                execution_time = time.time() - start_time
                sleep_time = max(0, self.config['check_interval'] - execution_time)
                
                logger.info(f"Próximo ciclo em {sleep_time:.0f} segundos...")
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logger.info("🛑 Bot parado pelo usuário")
                self.send_telegram_message("🛑 Bot parado.")
                break
            except Exception as e:
                logger.error(f"Erro no loop principal: {e}")
                time.sleep(60)  # Espera 1 minuto em caso de erro

def main():
    """Função principal"""
    try:
        bot = SimpleCryptoBot()
        bot.start_monitoring()
    except Exception as e:
        logger.error(f"Erro crítico: {e}")
        print(f"ERRO: {e}")

if __name__ == "__main__":
    main()
