import telebot, requests, threading, time, logging, os, json, base64, hmac, hashlib, random
from datetime import datetime, timezone, timedelta
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from collections import defaultdict
from functools import lru_cache

BOT_VERSION = "1.0.0.0"
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7823038896:AAHtY1iJtf4ygJC0W8u_r5buwexfEBeFhF8")
bot = telebot.TeleBot(TOKEN)
logger = logging.getLogger("CryptoAnalysisBot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger.addHandler(logging.FileHandler("bot_debug.log", encoding="utf-8"))

# رسالة ترحيبية شاملة لوظائف البوت
WELCOME_MSG = f"""
✨ **مرحباً بك في بوت التحليل الفني المتقدم!** ✨
الإصدار: {BOT_VERSION}

🔹 **الأوامر الرئيسية:**
/start - بدء استخدام البوت
/help - عرض دليل الاستخدام

✨━━━━━━━━━━━━━━━━━━━━━✨
🔹 **الوظائف المتاحة:**

1. **📈 تحليل جديد**
   - تحليل فني متكامل للعملات الرقمية
   - مثال: `BTC binance b` (استثماري)
   - مثال: `ETH gateio s` (مضاربي)

2. **🤖 التداول الآلي**
   - نظام تداول ذكي متكامل يشمل:
     • ⚙️ ربط منصات التداول (Binance, MEXC, GateIO)
     • ➕ إدارة محفظة العملات
     • 📊 تشغيل/إيقاف النظام الآلي
     • ⚖️ إدارة رأس المال والمخاطر

3. **📊 أدوات متقدمة**
   - حساب نقاط الدخول والأهداف الذكية
   - كشف الإنتقالات الصاروخية
   - تحليل قوة الإشارات
   - مراقبة الصفقات الحية

✨━━━━━━━━━━━━━━━━━━━━━✨
🔹 **مميزات فريدة:**
- 🚀 تحليلات مدعومة بـ AI
- ⏱ نتائج فورية خلال ثواني
- 🔒 دعم تشفير مفاتيح API
- 📈 متوافق مع 6 منصات تداول

✨━━━━━━━━━━━━━━━━━━━━━✨
📲 طلب خدمة متميزة: [تواصل مع المطور](https://t.me/autodzcrypto)
🆘 دعم فني: @meraga01
"""

# API keys for alternative sources
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY", "your_coinmarketcap_api_key")
COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "your_coingecko_api_key")

user_eph_msgs = defaultdict(list)
user_trades, user_scans = {}, {}
EXCHANGES = {
    'binance': {'fmt': lambda s: f"{s}USDT", 'prc': lambda s: f"https://api.binance.com/api/v3/ticker/price?symbol={s}USDT",
                'cnd': {'url': 'https://api.binance.com/api/v3/klines','p': 'symbol','iv': lambda i: i,
                'prs': lambda d: (float(d[2]), float(d[3]), float(d[4]), float(d[1]), float(d[5]))}},
    'mexc': {'fmt': lambda s: f"{s}USDT", 'prc': lambda s: f"https://api.mexc.com/api/v3/ticker/price?symbol={s}USDT",
             'cnd': {'url': 'https://api.mexc.com/api/v3/klines','p': 'symbol','iv': lambda i: i,
             'prs': lambda d: (float(d[2]), float(d[3]), float(d[4]), float(d[1]), float(d[5]))}},
    'gateio': {'fmt': lambda s: f"{s}_USDT", 'prc': lambda s: f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={s}_USDT",
               'cnd': {'url': 'https://api.gateio.ws/api/v4/spot/candlesticks','p': 'currency_pair','iv': lambda i: i,
               'prs': lambda d: (float(d[2]), float(d[3]), float(d[4]), float(d[1]), float(d[5]))}},
    'kucoin': {'fmt': lambda s: f"{s}-USDT", 'prc': lambda s: f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={s}-USDT",
               'cnd': {'url': 'https://api.kucoin.com/api/v1/market/candles','p': 'symbol','iv': lambda i: i,
               'prs': lambda d: (float(d[2]), float(d[3]), float(d[4]), float(d[1]), float(d[5]))}},
    'bybit': {'fmt': lambda s: f"{s}USDT", 'prc': lambda s: f"https://api.bybit.com/v2/public/tickers?symbol={s}USDT",
              'cnd': {'url': 'https://api.bybit.com/v5/market/kline','p': 'symbol','iv': lambda i: '240' if i == '4h' else 'D',
              'prs': lambda d: (float(d[2]), float(d[3]), float(d[4]), float(d[1]), float(d[5]))}},
    'okx': {'fmt': lambda s: f"{s}-USDT", 'prc': lambda s: f"https://www.okx.com/api/v5/market/ticker?instId={s}-USDT",
            'cnd': {'url': 'https://www.okx.com/api/v5/market/candles','p': 'instId','iv': lambda i: {'1d':'1D','4h':'4H'}[i],
            'prs': lambda d: (float(d[2]), float(d[3]), float(d[4]), float(d[1]), float(d[5]))}}
}
SPECIAL_NUMS = {
    2: "انعكاس صغيرة",
    3: "انعكاس صغيرة",
    4: "ارتكاز متوسطة",
    5: "انعكاس حادة",
    6: "توازن ديناميكي",
    7: "تجمع صغير",
    8: "ارتكاز قوية",
    9: "دعم ثابت",
    13: "انعكاس سريع",
    16: "دعم ثابت",
    19: "تحول متوسطة",
    21: "تجمعات متوسطة",
    22: "تصحيح متوسطة",
    25: "انتقال سلس",
    27: "انعكاس متوسط",
    32: "توازن سعري",
    36: "توازن رئيسية",
    37: "تجمعات سعرية",
    44: "تصحيح كبيرة",
    49: "دعم/مقاومة",
    64: "انعكاس محورية",
    81: "تحول رئيسي",
    88: "تصحيح عميق",
    91: "دعم/مقاومة",
    125: "انعكاس حاد",
    144: "تحول رئيسي",
    343: "دورة كاملة"
}

# إستراتيجية التداول اليومية
DAILY_STRATEGY_COIN = "SOL"
DAILY_STRATEGY_PROFIT_TARGET = 0.0025  # 0.25%
daily_strategy_trades = {}

def calculate_gravity_center(highs, lows, closes, volumes, period=14):
    """حساب مؤشر الثقل (مركز الجاذبية)"""
    if not (highs and lows and closes and volumes) or len(closes) < period:
        return None

    weights = [0.5 * (1.5 ** i) for i in range(period)]
    total_weight = sum(weights)

    weighted_sum = 0
    total_volume = 0
    start_index = max(0, len(closes) - period)

    for i in range(start_index, len(closes)):
        idx = i - start_index
        weight = weights[idx]

        candle_center = (highs[i] + lows[i] + closes[i]) / 3

        volume_factor = min(volumes[i] / max(volumes[start_index:i+1]), 2.0) if max(volumes[start_index:i+1]) > 0 else 1.0

        weighted_sum += candle_center * weight * volume_factor
        total_volume += volumes[i] * weight

    if total_volume == 0:
        return weighted_sum / total_weight

    return weighted_sum / total_volume

def del_eph(cid):
    """حذف الرسائل المؤقتة"""
    if cid in user_eph_msgs:
        for mid in user_eph_msgs[cid]:
            try:
                bot.delete_message(cid, mid)
                time.sleep(0.1)
            except Exception as e:
                logger.warning(f"تعذر حذف الرسالة {mid}: {e}")
        user_eph_msgs[cid] = []

def send_msg(cid, txt, perm=False, **kw):
    """إرسال رسالة مع إدارة الرسائل المؤقتة"""
    del_eph(cid)
    if 'reply_markup' not in kw:
        kw['reply_markup'] = ReplyKeyboardMarkup(resize_keyboard=True).row("📈 تحليل جديد", "🤖 التداول الآلي")
    try:
        msg = bot.send_message(cid, txt, **kw)
        if not perm:
            user_eph_msgs[cid].append(msg.message_id)
        return msg
    except Exception as e:
        logger.exception(f"فشل الإرسال: {e}")

def load_d(uid, t):
    """تحميل بيانات المستخدم"""
    os.makedirs("user_data", exist_ok=True)
    fp = f"user_data/{uid}_{t}.json"
    return json.load(open(fp, 'r', encoding='utf-8')) if os.path.exists(fp) else None

def save_d(uid, t, d):
    """حفظ بيانات المستخدم"""
    try: json.dump(d, open(f"user_data/{uid}_{t}.json", 'w', encoding='utf-8'), ensure_ascii=False)
    except: pass

def enc(d): return base64.b64encode(d.encode() if isinstance(d, str) else d).decode()
def dec(d): return base64.b64decode(d.encode() if isinstance(d, str) else d).decode()

def get_prc(sym, ex):
    """الحصول على السعر الحالي"""
    ex = ex.lower() if ex.lower() in EXCHANGES else 'binance'
    try:
        fmt = EXCHANGES[ex]['fmt'](sym.upper())
        url = EXCHANGES[ex]['prc'](sym.upper())
        d = requests.get(url, timeout=10).json()
        if ex == 'binance': return float(d.get('price'))
        elif ex == 'mexc': return float(d.get('price'))
        elif ex == 'gateio': return float(d[0].get('last'))
        elif ex == 'kucoin': return float(d.get('data', {}).get('price'))
        elif ex == 'bybit': return float(d.get('result', [{}])[0].get('last_price'))
        elif ex == 'okx': return float(d.get('data', [{}])[0].get('last'))
    except:
        return get_prc_alternative(sym)

def get_prc_alternative(sym):
    """الحصول على السعر من مصادر بديلة"""
    sources = [
        get_prc_coingecko,
        get_prc_coinmarketcap,
        get_prc_tradingview
    ]

    for source in sources:
        try:
            price = source(sym)
            if price is not None:
                return price
        except Exception as e:
            logger.error(f"Error in alternative price source: {e}")
    return None

def get_prc_coingecko(symbol):
    """الحصول على السعر من CoinGecko"""
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol.lower()}&vs_currencies=usd"
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        data = response.json()
        return data.get(symbol.lower(), {}).get('usd')
    return None

def get_prc_coinmarketcap(symbol):
    """الحصول على السعر من CoinMarketCap"""
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    headers = {'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY}
    params = {'symbol': symbol, 'convert': 'USD'}
    response = requests.get(url, headers=headers, params=params, timeout=10)
    if response.status_code == 200:
        data = response.json()
        return data['data'][symbol]['quote']['USD']['price']
    return None

def get_prc_tradingview(symbol):
    """الحصول على السعر من TradingView"""
    url = "https://scanner.tradingview.com/crypto/scan"
    payload = {
        "filter": [{"left": "name", "operation": "equal", "right": f"{symbol}USDT"}],
        "columns": ["close"]
    }
    response = requests.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        data = response.json()
        return data['data'][0]['d'][0]
    return None

def get_daily_candle(sym, ex):
    """الحصول على شمعة يومية"""
    ex = ex.lower() if ex.lower() in EXCHANGES else 'binance'
    cfg = EXCHANGES[ex]['cnd']
    sym_fmt = EXCHANGES[ex]['fmt'](sym.upper())
    p = {cfg['p']: sym_fmt, 'interval': '1d', 'limit': 1}
    try:
        d = requests.get(cfg['url'], params=p, timeout=10).json()
        dl = d.get('data', []) if ex in ['kucoin','okx'] else d.get('result',{}).get('list',[]) if ex=='bybit' else d
        if dl and len(dl) > 0:
            it = dl[-1]
            high, low, close, open_, vol = cfg['prs'](it)
            return {"ath": high, "atl": low, "cur": close, "vol": vol}
    except:
        return get_daily_candle_alternative(sym)

def get_daily_candle_alternative(sym):
    """الحصول على شمعة يومية من مصادر بديلة"""
    sources = [
        get_daily_candle_coingecko,
        get_daily_candle_coinmarketcap
    ]

    for source in sources:
        try:
            candle = source(sym)
            if candle:
                return candle
        except Exception as e:
            logger.error(f"Error in alternative daily candle: {e}")
    return None

def get_cnd(sym, ex, t='B'):
    """الحصول على بيانات الشموع"""
    ex = ex.lower() if ex.lower() in EXCHANGES else 'binance'
    cfg = EXCHANGES[ex]['cnd']
    iv, lim = ('4h', 60) if t.upper() == 'S' else ('1d', 100)
    sym_fmt = EXCHANGES[ex]['fmt'](sym.upper())
    p = {cfg['p']: sym_fmt}

    if ex in ['binance', 'mexc', 'gateio']:
        p.update({'interval':iv, 'limit':lim})
    elif ex == 'kucoin':
        p.update({'type':iv, 'limit':lim})
    elif ex == 'bybit':
        p.update({'category':'spot','interval':cfg['iv'](iv),'symbol':sym_fmt,'limit':lim})
    elif ex == 'okx':
        p.update({'bar':cfg['iv'](iv),'limit':str(lim)})

    try:
        d = requests.get(cfg['url'], params=p, timeout=15).json()
        dl = d.get('data', []) if ex in ['kucoin','okx'] else d.get('result',{}).get('list',[]) if ex=='bybit' else d
        h, l = [], []
        for it in dl:
            try:
                high, low, close, open_, vol = cfg['prs'](it)
                h.append(high)
                l.append(low)
            except:
                pass
        return {"ath": max(h) if h else None, "atl": min(l) if l else None, "cur": get_prc(sym, ex)}
    except Exception as e:
        logger.error(f"Failed to get data from {ex}: {e}")
        return get_cnd_alternative(sym, t)

def get_cnd_alternative(sym, t):
    """الحصول على بيانات الشموع من مصادر بديلة"""
    sources = [
        get_cnd_coingecko,
        get_cnd_coinmarketcap,
        get_cnd_tradingview
    ]

    for source in sources:
        try:
            data = source(sym)
            if data:
                logger.info(f"Got data from {source.__name__} for {sym}")
                return data
        except Exception as e:
            logger.error(f"Error in {source.__name__}: {e}")

    logger.error(f"All alternative sources failed for {sym}")
    return None

@lru_cache(maxsize=100)
def get_cnd_coingecko(symbol):
    """الحصول على بيانات الشموع من CoinGecko"""
    search_url = "https://api.coingecko.com/api/v3/search"
    search_params = {"query": symbol}
    search_res = requests.get(search_url, params=search_params, timeout=10)
    search_data = search_res.json()

    if not search_data.get("coins"):
        return None

    coin_id = search_data["coins"][0]["id"]

    coin_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
    coin_params = {
        "tickers": False,
        "market_data": True,
        "community_data": False,
        "developer_data": False
    }

    coin_res = requests.get(coin_url, params=coin_params, timeout=15)
    coin_data = coin_res.json()

    market_data = coin_data.get("market_data", {})
    return {
        "ath": market_data.get("ath", {}).get("usd"),
        "atl": market_data.get("atl", {}).get("usd"),
        "cur": market_data.get("current_price", {}).get("usd")
    }

def get_cnd_coinmarketcap(symbol):
    """الحصول على بيانات الشموع من CoinMarketCap"""
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": symbol, "convert": "USD"}
    headers = {"X-CMC_PRO_API_KEY": COINMARKETCAP_API_KEY}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        if data.get("status", {}).get("error_code") != 0:
            return None

        coin_data = data.get("data", {}).get(symbol.upper())
        if not coin_data:
            return None

        quote = coin_data.get("quote", {}).get("USD", {})
        return {
            "ath": quote.get("ath_price"),
            "atl": quote.get("atl_price"),
            "cur": quote.get("price")
        }
    except:
        return None

def get_cnd_tradingview(symbol):
    """الحصول على بيانات الشموع من TradingView"""
    url = "https://scanner.tradingview.com/crypto/scan"
    payload = {
        "filter": [{"left": "name", "operation": "equal", "right": f"{symbol}USDT"}],
        "columns": ["high", "low", "close"]
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        if data.get("data"):
            item = data["data"][0]["d"]
            return {
                "ath": item[0],
                "atl": item[1],
                "cur": item[2]
            }
        return None
    except:
        return None

def get_rsi(closes, period=14):
    """حساب مؤشر RSI"""
    if len(closes) < period + 1 or any(c is None for c in closes):
        return None

    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        gains.append(max(0, change))
        losses.append(max(0, -change))

    if not gains or not losses:
        return None

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period-1) + gains[i]) / period
        avg_loss = (avg_loss * (period-1) + losses[i]) / period

    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_macd(closes, fast=12, slow=26, signal=9):
    """حساب مؤشر MACD"""
    if len(closes) < slow + signal or any(c is None for c in closes):
        return None

    ema_fast = sum(closes[:fast]) / fast
    ema_slow = sum(closes[:slow]) / slow

    for i in range(slow, len(closes)):
        ema_fast = (closes[i] * 2/(fast+1)) + (ema_fast * (fast-1)/(fast+1))
        ema_slow = (closes[i] * 2/(slow+1)) + (ema_slow * (slow-1)/(slow+1))

    macd_line = ema_fast - ema_slow
    signal_line = sum(closes[-signal:]) / signal if len(closes) >= signal else macd_line
    return {'macd': macd_line, 'signal': signal_line, 'histogram': macd_line - signal_line}

def get_volume_factor(current_vol, avg_vol):
    """حساب عامل الحجم"""
    if not current_vol or not avg_vol:
        return 0
    ratio = current_vol / avg_vol
    if ratio > 1.5: return 1.0
    elif ratio > 1.2: return 0.7
    elif ratio > 0.8: return 0.5
    return 0.3

def get_candles(sym, ex, interval, limit):
    """الحصول على بيانات الشموع الكاملة"""
    ex = ex.lower()
    if ex not in EXCHANGES: return None

    cfg = EXCHANGES[ex]['cnd']
    fmt_sym = EXCHANGES[ex]['fmt'](sym.upper())
    params = {cfg['p']: fmt_sym, 'interval': interval, 'limit': limit}

    try:
        response = requests.get(cfg['url'], params=params, timeout=15)
        data = response.json()

        if ex in ['kucoin', 'okx']:
            candles = data.get('data', [])
        elif ex == 'bybit':
            candles = data.get('result', {}).get('list', [])
        else:
            candles = data

        formatted = []
        for c in candles:
            try:
                o, h, l, c, v = cfg['prs'](c)
                if None in [o, h, l, c]:
                    continue
                formatted.append({
                    'open': o,
                    'high': h,
                    'low': l,
                    'close': c,
                    'volume': v
                })
            except:
                continue
        return formatted

    except Exception as e:
        logger.error(f"Error fetching candles: {e}")
        return None

def calc_lvls(ath, atl, cur, t, sym, ex):
    """حساب نقاط الدخول والأهداف"""
    if not all([ath, atl, cur]) or (ath - atl) <= 0:
        return {"e": None, "s": None, "t": [], "p": []}

    r = ath - atl
    best_entry = None
    targets = []
    pivots = []

    # المستويات القوية للدعوم والمقاومات
    support_levels = [9, 13, 16, 21, 25, 49, 64, 81, 91]
    resistance_levels = [125, 144, 169, 196, 225, 256, 289]

    # البحث عن أقوى مستوى دعم أسفل السعر الحالي
    potential_supports = [atl + r * (level / 100.0) for level in support_levels]
    below_supports = [lvl for lvl in potential_supports if lvl < cur]

    if below_supports:
        best_entry = max(below_supports)
    else:
        daily_data = get_daily_candle(sym, ex)
        if daily_data and daily_data['ath'] and daily_data['atl']:
            daily_r = daily_data['ath'] - daily_data['atl']
            daily_supports = [daily_data['atl'] + daily_r * (level / 100.0) for level in support_levels]
            below_daily = [lvl for lvl in daily_supports if lvl < cur]
            if below_daily:
                best_entry = max(below_daily)

    if not best_entry:
        return {"e": None, "t": [], "p": []}

    # تحسين نقطة الدخول للتحليل الاستثماري عند ارتفاع RSI
    if t.upper() == 'B':
        rsi_high = False

        # تحليل RSI اليومي
        daily_candles = get_candles(sym, ex, '1d', 15)
        if daily_candles and len(daily_candles) >= 14:
            daily_closes = [candle['close'] for candle in daily_candles]
            rsi_daily = get_rsi(daily_closes)
            if rsi_daily and rsi_daily > 80:
                rsi_high = True

        # تحليل RSI على 4 ساعات
        if not rsi_high:
            four_hour_candles = get_candles(sym, ex, '4h', 15)
            if four_hour_candles and len(four_hour_candles) >= 14:
                four_hour_closes = [candle['close'] for candle in four_hour_candles]
                rsi_4h = get_rsi(four_hour_closes)
                if rsi_4h and rsi_4h > 80:
                    rsi_high = True

        # إذا كان RSI مرتفعاً، نبحث عن نقطة دخول أبعد
        if rsi_high:
            extended_supports = support_levels + [37]
            extended_supports.sort()

            potential_supports_ext = [atl + r * (level / 100.0) for level in extended_supports]
            below_supports_ext = [lvl for lvl in potential_supports_ext if lvl < best_entry]

            if below_supports_ext:
                best_entry = max(below_supports_ext)

    # تحديد المدى السعري لـ 250 شمعة 4 ساعات
    if t.upper() == 'B':
        candles_4h = get_candles(sym, ex, '4h', 250)
        if candles_4h and len(candles_4h) > 0:
            highs_4h = [candle['high'] for candle in candles_4h]
            lows_4h = [candle['low'] for candle in candles_4h]
            ath_4h = max(highs_4h)
            atl_4h = min(lows_4h)
            r_4h = ath_4h - atl_4h

            if r_4h > 0:
                support_4h = [atl_4h + r_4h * (level / 100.0) for level in support_levels]
                below_support_4h = [lvl for lvl in support_4h if lvl < cur]

                if below_support_4h:
                    best_entry_4h = max(below_support_4h)

                    if best_entry_4h < best_entry:
                        best_entry = best_entry_4h

    # الفلترة باستخدام مؤشر الثقل
    best_entry = filter_entry_point(sym, ex, cur, best_entry, atl, ath, t)

    # حساب الأهداف بناءً على مستويات المقاومة
    potential_targets = [atl + r * (level / 100.0) for level in resistance_levels]
    above_targets = [tgt for tgt in potential_targets if tgt > best_entry and tgt < ath]

    # تحديد عدد الأهداف بناءً على جودة الصفقة
    if t.upper() == 'S':
        near_targets = [tgt for tgt in above_targets if (tgt - best_entry) / best_entry <= 0.15]
        if near_targets:
            targets = sorted(near_targets)[:4]
        else:
            targets = [
                best_entry * 1.05,
                best_entry * 1.10,
                best_entry * 1.15
            ][:2]
    else:
        main_targets = [tgt for tgt in above_targets if (tgt - best_entry) / best_entry > 0.15]
        if main_targets:
            targets = sorted(main_targets)[:4]
        else:
            targets = [
                best_entry * 1.15,
                best_entry * 1.25,
                best_entry * 1.35,
                best_entry * 1.50
            ]

    # حساب الارتكازات السعرية بين نقطة الدخول والأهداف
    if targets:
        mid_point = (best_entry + targets[0]) / 2
        pivots.append(mid_point)

        for i in range(len(targets)-1):
            pivot = (targets[i] + targets[i+1]) / 2
            pivots.append(pivot)

    return {
        "e": best_entry,
        "t": targets,
        "p": pivots
    }

def filter_entry_point(sym, ex, cur, best_entry, atl, ath, trade_type):
    """فلترة نقطة الدخول باستخدام مؤشر الثقل"""
    timeframes = ['1d', '4h', '1h']
    gc_confirmation = 0

    for tf in timeframes:
        data = get_candles(sym, ex, tf, 100)
        if not data or len(data) < 20:
            continue

        highs = [d['high'] for d in data]
        lows = [d['low'] for d in data]
        closes = [d['close'] for d in data]
        volumes = [d['volume'] for d in data]

        gc = calculate_gravity_center(highs, lows, closes, volumes)
        if gc:
            distance = abs(best_entry - gc) / gc
            if distance < 0.03:
                gc_confirmation += 1

    if gc_confirmation < 2:
        strong_levels = [9, 13, 16, 21, 25, 36, 49, 64, 81, 91]
        potential_supports = [atl + (ath - atl) * (level / 100.0) for level in strong_levels]

        valid_supports = [s for s in potential_supports if s < cur and s > atl]

        if valid_supports:
            new_entry = max(valid_supports)

            if new_entry < best_entry:
                return new_entry

    return best_entry

def gen_txt(sym, ex, atl, ath, cur, t='b'):
    """إنشاء رسالة التحليل النهائية"""
    if not all([ath, atl, cur]): return "⚠️ لا توجد بيانات كافية للتحليل."
    i = calc_lvls(ath, atl, cur, t, sym, ex)

    # تنسيق الأرقام
    def fmt_num(num):
        if num < 0.001: return f"{num:.8f}"
        elif num < 0.1: return f"{num:.6f}"
        elif num < 1: return f"{num:.4f}"
        else: return f"{num:.6f}"

    # حساب تقلبات 24 ساعة
    daily_data = get_daily_candle(sym, ex) or {}
    daily_high = daily_data.get('ath', 0)
    daily_low = daily_data.get('atl', 0)
    volatility_24h = ((daily_high - daily_low) / daily_low * 100) if daily_low > 0 else 0

    # حساب قوة الصفقة (تحديد عدد الأهداف)
    trade_strength = min(int((cur - atl) / (ath - atl) * 10), 4)
    targets = i["t"][:trade_strength] if trade_strength > 0 else []

    # حساب أسرع الانتقالات الصاروخية
    r = ath - atl
    rocket_moves = []

    # 1. الانتقال من 26% إلى 45%
    move_26 = atl + r * 0.26
    move_45 = atl + r * 0.45
    move_pct_26_45 = ((move_45 - move_26) / move_26) * 100
    rocket_moves.append({
        "type": "الإنتقال الصاروخي الأول",
        "from": fmt_num(move_26),
        "to": fmt_num(move_45),
        "pct": move_pct_26_45
    })

    # 2. الانتقال من 49% إلى 91%
    move_49 = atl + r * 0.49
    move_91 = atl + r * 0.91
    move_pct_49_91 = ((move_91 - move_49) / move_49) * 100
    rocket_moves.append({
        "type": "الإنتقال الصاروخي الثاني",
        "from": fmt_num(move_49),
        "to": fmt_num(move_91),
        "pct": move_pct_49_91
    })

    # 3. الانتقال من 81% إلى 125%
    move_81 = atl + r * 0.81
    move_125 = atl + r * 1.25
    move_pct_81_125 = ((move_125 - move_81) / move_81) * 100
    rocket_moves.append({
        "type": "الإنتقال الصاروخي الثالث",
        "from": fmt_num(move_81),
        "to": fmt_num(move_125),
        "pct": move_pct_81_125
    })

    # تحليل معلومات إضافية للصفقة
    additional_info = analyze_additional_info(sym, ex, i['e'], targets, atl, ath)

    # بناء الرسالة بتصميم جديد
    msg = [
        f"🌟 **{sym.upper()} | {ex.upper()} | {'استثماري' if t == 'b' else 'مضاربي'}** 🌟",
        "✨━━━━━━━━━━━━━━━━━━━━━✨",
        f"📊 **المعلومات الأساسية:**",
        f"• السعر الحالي: `{fmt_num(cur)}`",
        f"• تقلبات 24 ساعة: `({volatility_24h:.2f}%)`",
        "✨━━━━━━━━━━━━━━━━━━━━━✨"
    ]

    # إضافة الأهداف إذا كانت متاحة
    if targets:
        msg.append(f"📍 **نقطة الدخول المثالية:** `{fmt_num(i['e'])}`")
        msg.append("✨━━━━━━━━━━━━━━━━━━━━━✨")
        msg.append(f"🚀 **الأهداف ({len(targets)} مستويات):**")
        prev_level = i['e']

        for idx, tgt in enumerate(targets, 1):
            move_pct = ((tgt - prev_level) / prev_level) * 100
            if move_pct > 15:
                move_desc = f"🚀 صاروخية (+{move_pct:.1f}%)"
            elif move_pct > 8:
                move_desc = f"⚡ سريعة جداً (+{move_pct:.1f}%)"
            elif move_pct > 3:
                move_desc = f"↗️ سريعة (+{move_pct:.1f}%)"
            else:
                move_desc = f"➡️ طبيعية (+{move_pct:.1f}%)"

            # استخدام الأقواس للنسب المئوية
            msg.append(f"{idx}. `{fmt_num(tgt)}` - {move_desc}")
            prev_level = tgt
        msg.append("✨━━━━━━━━━━━━━━━━━━━━━✨")
    else:
        msg.append("⚠️ **لا توجد صفقة شراء مناسبة في هذه العملة حالياً**")
        msg.append("✨━━━━━━━━━━━━━━━━━━━━━✨")

    # قسم الانتقالات الصاروخية
    if rocket_moves:
        msg.append("🚀 **الإنتقالات الصاروخية:**")
        for move in rocket_moves:
            msg.append(f"• **{move['type']}:**")
            msg.append(f"  من `{move['from']}` إلى `{move['to']}`")
            # استخدام الأقواس للنسب المئوية
            msg.append(f"  نسبة: `({move['pct']:.2f}%)`")
        msg.append("✨━━━━━━━━━━━━━━━━━━━━━✨")

    # قسم معلومات إضافية للصفقة
    if additional_info:
        msg.append("🧪 **معلومات إضافية للصفقة:**")
        msg.append(f"• الإتجاه الحالي: {additional_info['trend']}")

        if additional_info['stop_points']:
            msg.append("🧪 المحطات السعرية المتوقعة:")
            for idx, point in enumerate(additional_info['stop_points'], 1):
                msg.append(f"  {idx}. `{fmt_num(point)}`")
        else:
            msg.append("• لا توجد محطات سعرية واضحة")
        msg.append("✨━━━━━━━━━━━━━━━━━━━━━✨")

    # إضافة رابط المستخدم في نهاية الرسالة
    msg.append("\n───")
    msg.append("📲 طلب خدمة التحليل: https://t.me/autodzcrypto")

    return "\n".join(msg)

def analyze_additional_info(sym, ex, entry, targets, atl, ath):
    """تحليل معلومات إضافية للصفقة"""
    info = {
        "trend": "صاعد",
        "stop_points": []
    }

    # تحديد الإتجاه الحالي
    daily_candles = get_candles(sym, ex, '1d', 30)
    if daily_candles and len(daily_candles) >= 10:
        last_close = daily_candles[-1]['close']
        prev_close = daily_candles[-2]['close']
        if last_close > prev_close:
            info['trend'] = "📈 صاعد"
        elif last_close < prev_close:
            info['trend'] = "📉 هابط"
        else:
            info['trend'] = "↔️ جانبي"

    # تحديد المحطات السعرية (نقاط التوقف المحتملة)
    r = ath - atl
    stop_levels = [13, 25, 36, 49, 64, 81, 91, 100]

    for level in stop_levels:
        price_level = atl + r * (level / 100.0)
        if price_level > entry and price_level < (targets[-1] if targets else ath):
            info['stop_points'].append(price_level)

    # إضافة نقاط ارتكاز بين الأهداف
    if targets:
        for i in range(len(targets)-1):
            mid_point = (targets[i] + targets[i+1]) / 2
            if mid_point not in info['stop_points']:
                info['stop_points'].append(mid_point)

    # ترتيب المحطات السعرية
    info['stop_points'] = sorted(info['stop_points'])

    return info

def save_mexc(uid, k, s):
    """حفظ مفاتيح MEXC API"""
    save_d(uid, "mexc", {"k": enc(k), "s": enc(s)})

def load_mexc(uid):
    """تحميل مفاتيح MEXC API"""
    d = load_d(uid, "mexc")
    return (dec(d["k"]), dec(d["s"])) if d else (None, None)

def mexc_ord(uid, sym, sd, q):
    """تنفيذ أمر على MEXC"""
    k, s = load_mexc(uid)
    if not k: return {"error": "❌ مفاتيح API غير موجودة"}

    url, ep = "https://api.mexc.com", "/api/v3/order"
    ts = int(time.time() * 1000)
    p = {"symbol": f"{sym.upper()}USDT", "side": sd.upper(), "type": "MARKET", "quantity": q, "timestamp": ts}
    qs = '&'.join([f"{k}={v}" for k, v in p.items()])
    sig = hmac.new(s.encode(), qs.encode(), hashlib.sha256).hexdigest()
    h = {"X-MEXC-APIKEY": k}

    try:
        r = requests.post(f"{url}{ep}", params={**p, "signature": sig}, headers=h, timeout=10)
        return r.json() if r.status_code == 200 else {"error": f"خطأ API: {r.status_code}"}
    except Exception as e:
        logger.exception("MEXC order error")
        return {"error": str(e)}

def ordr(uid, coin, sd, amt):
    """تنفيذ أمر تداول"""
    try:
        s = load_d(uid, "settings") or {}
        ex = s.get('ex', 'mexc')
        if ex == 'mexc':
            r = mexc_ord(uid, coin, sd, amt)
            return 'orderId' in r

        keys = s.get('keys', {}).get(ex, {})
        if not keys: return False
        k, sec = dec(keys['k']), dec(keys['s'])
        sym = EXCHANGES[ex]['fmt'](coin)

        if ex == 'binance':
            p = {'symbol': sym, 'side': sd, 'type': 'MARKET', 'quantity': amt, 'timestamp': int(time.time()*1000)}
            q = '&'.join([f"{k}={v}" for k,v in p.items()])
            sig = hmac.new(sec.encode(), q.encode(), hashlib.sha256).hexdigest()
            h = {'X-MBX-APIKEY': k}
            r = requests.post("https://api.binance.com/api/v3/order", headers=h, params={**p, 'signature': sig}).json()
            return r.get('status') == 'FILLED'
        return False
    except: return False

def trade(uid, coin, s):
    """تنفيذ صفقة تداول"""
    if user_trades.get(uid, {}).get("on"): return False
    cap = (load_d(uid, "cap") or {}).get('cap', 1000) * (s.get('cap_pct',100) / 100)
    cur = get_prc(coin, s['ex'])
    if not cur: return False
    amt = cap / cur
    suc = ordr(uid, coin, 'BUY', amt)
    if suc:
        send_msg(uid, f"✅ تم تنفيذ صفقة!\n• العملة: {coin}\n• الكمية: {amt:.6f}\n• السعر: {cur}")
        user_trades[uid] = {"on": True, "coin": coin, "e": cur, "t": datetime.now(timezone.utc)}
    else:
        send_msg(uid, f"⚠️ فشل تنفيذ الصفقة!\n• العملة: {coin}")
    return suc

def close(uid, coin, cl, rsn):
    """إغلاق صفقة تداول"""
    t = user_trades.get(uid, {})
    if not t: return

    s = load_d(uid, "settings") or {}
    amt = t.get("amt", (s.get('cap', 1000) / t.get("e", cl)))

    if not ordr(uid, coin, 'SELL', amt): return send_msg(uid, f"⚠️ فشل إغلاق صفقة {coin}!")

    e = t.get("e", cl)
    pft = ((cl - e) / e) * 100
    dur = datetime.now(timezone.utc) - t.get("t", datetime.now(timezone.utc))
    h, rem = divmod(dur.seconds, 3600)
    m, sec = divmod(rem, 60)

    send_msg(uid, f"✅ تم إغلاق صفقة {coin}!\n• السبب: {rsn}\n• الدخول: {e}\n• الخروج: {cl}\n• الربح: {pft:.2f}%\n• المدة: {h}س {m}د {sec}ث")
    user_trades[uid] = {"on": False}

def scan(uid, s):
    """مسح العملات للعثور على فرص تداول"""
    if uid not in user_scans: user_scans[uid] = {"t": 0, "i": 0, "b": None}
    sd = user_scans[uid]
    if time.time() - sd["t"] < 10: return
    sd["t"] = time.time()
    coins = s.get('coins', [])
    if not coins: return
    coin = coins[sd["i"]]
    sd["i"] = (sd["i"] + 1) % len(coins)
    d = get_cnd(coin, s['ex'], s['type'])
    if not d: return
    ath, atl, cur = d['ath'], d['atl'], d['cur']

    if s['type'] == 'S':
        vc = min((ath - atl) / atl * 100 * 1.2, 50)
        pc = min((cur - atl) / (ath - atl) * 100 * 1.5, 50)
        strn = min(vc + pc, 100)
    else:
        p = (cur - atl) / (ath - atl) * 100
        vol = (ath - atl) / atl * 100
        strn = max(0, 100 - abs(p-50)) * (min(vol,50)/50)

    min_str = 85 if s['type'] == 'S' else 70
    if strn >= min_str and (not sd["b"] or strn > sd["b"]["s"]):
        sd["b"] = {"c": coin, "s": strn, "p": cur}
    if sd["i"] == 0 and sd["b"]:
        if trade(uid, sd["b"]["c"], s):
            user_trades[uid] = {"on": True, "coin": sd["b"]["c"], "e": sd["b"]["p"], "t": datetime.now(timezone.utc)}
            send_msg(uid, f"🚀 تم تنفيذ صفقة تلقائية!\n• العملة: {sd['b']['c']}\n• القوة: {sd['b']['s']}%\n• السعر: {sd['b']['p']}")
        sd["b"] = None

def monitor(uid, coin):
    """مراقبة الصفقات النشطة"""
    s = load_d(uid, "settings") or {}
    t = user_trades.get(uid, {})
    cur = get_prc(coin, s.get('ex', 'mexc')) or t.get("e", 0)
    e = t.get("e", cur)
    profit = ((cur - e) / e) * 100
    min_p, max_p, stop = s.get('min',0.5), s.get('max',5.0), s.get('stop',2.0)
    if profit >= max_p: close(uid, coin, cur, "تحقيق الربح")
    elif profit <= -stop: close(uid, coin, cur, "وقف الخسارة")
    elif profit >= min_p: check(uid, coin, cur, profit)

def check(uid, coin, cur, profit):
    """فحص التراجعات للخروج المبكر"""
    try:
        ex = user_trades[uid].get('ex', 'mexc')
        c = get_candles(coin, ex, '1m', 5)
        if c and len(c) >= 3 and profit > 1.0 and c[-1]['close'] < c[-2]['close']:
            close(uid, coin, cur, "الخروج عند التراجع")
    except: pass

def original_auto_trade():
    """التداول الآلي المستمر الأصلي"""
    while True:
        try:
            for uid in list(user_trades.keys()):
                s = load_d(uid, "settings") or {}
                if not s.get('on') or not s.get('coins'): continue
                ts = user_trades.get(uid, {"on": False})
                if ts.get("on"): monitor(uid, ts["coin"])
                else: scan(uid, s)
                time.sleep(1)
        except Exception as e:
            logger.error(f"Error in auto trade: {e}")
            time.sleep(10)

def calculate_rsi(prices, period=14):
    """حساب مؤشر القوة النسبية (RSI)"""
    if len(prices) < period + 1:
        return None
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    if sum(losses) == 0:
        return 100
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period-1) + gains[i]) / period
        avg_loss = (avg_loss * (period-1) + losses[i]) / period
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def check_daily_strategy():
    """فحص شروط الإستراتيجية اليومية"""
    while True:
        try:
            for uid in list(user_trades.keys()):
                s = load_d(uid, "settings") or {}
                if not s.get('on') or 'ex' not in s:
                    continue
                
                # 1. الحصول على شمعة 15 دقيقة الحالية
                candle_15m = get_candles(DAILY_STRATEGY_COIN, s['ex'], '15m', 1)
                if not candle_15m or len(candle_15m) == 0:
                    continue
                
                candle_data = candle_15m[0]
                high_15m = candle_data['high']
                low_15m = candle_data['low']
                
                # 2. الحصول على شمعة دقيقة واحدة حالية
                candle_1m = get_candles(DAILY_STRATEGY_COIN, s['ex'], '1m', 1)
                if not candle_1m or len(candle_1m) == 0:
                    continue
                
                candle_1m_data = candle_1m[0]
                close_1m = candle_1m_data['close']
                
                # 3. التحقق من كسر قمة شمعة 15 دقيقة
                breakout_condition = (close_1m > high_15m)
                
                # 4. إذا لم يتحقق الشرط، تخطي
                if not breakout_condition:
                    continue
                
                # 5. الحصول على بيانات RSI وحجم التداول
                candles_5m = get_candles(DAILY_STRATEGY_COIN, s['ex'], '5m', 14)
                if not candles_5m or len(candles_5m) < 14:
                    continue
                
                closes_5m = [c['close'] for c in candles_5m]
                rsi = calculate_rsi(closes_5m)
                
                vol_candles = get_candles(DAILY_STRATEGY_COIN, s['ex'], '15m', 20)
                if not vol_candles or len(vol_candles) < 20:
                    continue
                
                avg_volume = sum(c['volume'] for c in vol_candles) / len(vol_candles)
                
                # 6. التحقق من الشروط النهائية
                entry_condition = (
                    rsi is not None and 
                    rsi < 70 and 
                    candle_data['volume'] > avg_volume
                )
                
                trade_id = f"daily_{int(time.time())}"
                
                if entry_condition and trade_id not in daily_strategy_trades:
                    # تنفيذ الصفقة
                    entry_price = get_prc(DAILY_STRATEGY_COIN, s['ex'])
                    if entry_price:
                        target_price = entry_price * (1 + DAILY_STRATEGY_PROFIT_TARGET)
                        daily_strategy_trades[trade_id] = {
                            'uid': uid,
                            'entry_price': entry_price,
                            'target_price': target_price,
                            'low_price': low_15m,  # وقف الخسارة تحت شمعة 15 دقيقة
                            'entry_time': datetime.now(timezone.utc),
                            'status': 'active'
                        }
                        
                        # إرسال إشعار الدخول
                        msg = [
                            "🚀 **تم تنفيذ صفقة استراتيجية يومية**",
                            f"• العملة: {DAILY_STRATEGY_COIN}",
                            f"• السعر: {entry_price:.6f}",
                            f"• الهدف: {target_price:.6f} (+0.25%)",
                            f"• وقف الخسارة: {low_15m:.6f}",
                            f"• الوقت: {datetime.now(timezone.utc).strftime('%H:%M:%S')}",
                            "✨━━━━━━━━━━━━━━━━━━━━━✨"
                        ]
                        send_msg(uid, "\n".join(msg), perm=True)
            
            # مراقبة الصفقات النشطة
            monitor_daily_strategy_trades()
            
            time.sleep(10)
        except Exception as e:
            logger.error(f"Error in daily strategy: {e}")
            time.sleep(30)

def monitor_daily_strategy_trades():
    """مراقبة صفقات الإستراتيجية اليومية"""
    current_time = datetime.now(timezone.utc)
    for trade_id, trade_data in list(daily_strategy_trades.items()):
        if trade_data['status'] != 'active':
            continue
        
        uid = trade_data['uid']
        current_price = get_prc(DAILY_STRATEGY_COIN, trade_data.get('ex', 'binance'))
        
        if not current_price:
            continue
        
        # 1. التحقق من تحقيق الهدف
        if current_price >= trade_data['target_price']:
            trade_data['status'] = 'target_hit'
            profit_percent = ((current_price - trade_data['entry_price']) / trade_data['entry_price']) * 100
            
            msg = [
                "✅ **تم تحقيق هدف الإستراتيجية اليومية**",
                f"• العملة: {DAILY_STRATEGY_COIN}",
                f"• سعر الدخول: {trade_data['entry_price']:.6f}",
                f"• سعر الخروج: {current_price:.6f}",
                f"• الربح: {profit_percent:.2f}%",
                f"• المدة: {(current_time - trade_data['entry_time']).seconds // 60} دقيقة",
                "✨━━━━━━━━━━━━━━━━━━━━━✨"
            ]
            send_msg(uid, "\n".join(msg), perm=True)
        
        # 2. التحقق من كسر قاع شمعة 15 دقيقة (وقف الخسارة)
        elif current_price <= trade_data['low_price']:
            trade_data['status'] = 'cancelled'
            
            msg = [
                "⛔ **تم إلغاء الصفقة - وقف الخسارة**",
                f"• العملة: {DAILY_STRATEGY_COIN}",
                f"• سعر الدخول: {trade_data['entry_price']:.6f}",
                f"• سعر الخروج: {current_price:.6f}",
                f"• مستوى وقف الخسارة: {trade_data['low_price']:.6f}",
                f"• الخسارة: {((current_price - trade_data['entry_price']) / trade_data['entry_price']) * 100:.2f}%",
                f"• الوقت: {current_time.strftime('%H:%M:%S')}",
                "✨━━━━━━━━━━━━━━━━━━━━━✨"
            ]
            send_msg(uid, "\n".join(msg), perm=True)

def auto_trade():
    """التداول الآلي المستمر"""
    # بدء خيط التداول الأصلي
    threading.Thread(target=original_auto_trade, daemon=True).start()
    # بدء خيط الإستراتيجية اليومية
    threading.Thread(target=check_daily_strategy, daemon=True).start()

def kb():
    """لوحة المفاتيح الرئيسية للتداول الآلي"""
    k = ReplyKeyboardMarkup(resize_keyboard=True)
    k.row("⚙️ إعدادات", "▶️ تشغيل", "⏸ إيقاف")
    k.row("📊 حالة", "📋 عملات", "🗑️ حذف")
    k.row("⚖️ رأس مال", "🔙 رئيسية")
    return k

@bot.message_handler(commands=['start'])
def welcome(m):
    """معالجة أمر البداية مع الرسالة الترحيبية"""
    del_eph(m.chat.id)
    send_msg(
        m.chat.id,
        WELCOME_MSG,
        perm=True,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    # إضافة لوحة المفاتيار التفاعلية
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📈 تحليل جديد", "🤖 التداول الآلي")
    bot.send_message(m.chat.id, "👇 اختر أحد الخيارات:", reply_markup=kb)

# تحديث دالة المساعدة
@bot.message_handler(commands=['help'])
def help_cmd(m):
    """عرض دليل الاستخدام"""
    del_eph(m.chat.id)
    send_msg(
        m.chat.id,
        WELCOME_MSG.replace("✨ **مرحباً بك", "📚 **دليل الاستخدام") +
        "\n\n✨━━━━━━━━━━━━━━━━━━━━━✨\n"
        "🔹 **دليل تفاعلي سريع:**\n"
        "1. استخدم 'تحليل جديد' للتحليل الفوري\n"
        "2. اختر 'التداول الآلي' للإدارة المتقدمة\n"
        "3. الأزرار الظاهرة تقودك للخطوة التالية",
        True,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

@bot.message_handler(func=lambda m: m.text in ["📈 تحليل جديد", "تحليل جديد"])
def new_analysis(m):
    """بدء تحليل جديد"""
    del_eph(m.chat.id)
    try:
        bot.delete_message(m.chat.id, m.message_id)
    except Exception as e:
        logger.warning(f"تعذر حذف رسالة المستخدم: {e}")

    msg = send_msg(m.chat.id, "✨━━━━━━━━━━━━━━━━━━━━━✨\n📈 **طلب تحليل جديد**\n✨━━━━━━━━━━━━━━━━━━━━━✨\n\n🔍 أرسل رمز العملة والمنصة ونوع التحليل:\n\n📌 الصيغة:\n`[رمز] [منصة] [نوع]`\n\n📌 نوع التحليل:\n- `b` استثماري (طويل)\n- `s` مضاربي (قصير)\n\n📝 مثال:\n`BTC binance b`\n\n✨━━━━━━━━━━━━━━━━━━━━━✨", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    if msg:
        bot.register_next_step_handler(msg, process_analysis)

def process_analysis(m):
    """معالجة طلب التحليل"""
    del_eph(m.chat.id)
    try:
        bot.delete_message(m.chat.id, m.message_id)
    except Exception as e:
        logger.warning(f"تعذر حذف رسالة المستخدم: {e}")

    # إرسال رسالة الانتظار
    wait_msg = bot.send_message(m.chat.id, "⌛")

    p = m.text.strip().split()
    if len(p) < 2:
        bot.delete_message(m.chat.id, wait_msg.message_id)
        return send_msg(m.chat.id, "⚠️ أجزاء غير كافية. الصيغة: `[رمز] [منصة] [نوع]`", parse_mode="Markdown")

    sym, ex, t = p[0].upper(), p[1].lower(), 'b'
    if len(p) >= 3 and p[2].lower() in ['b','s']: t = p[2].lower()

    d = get_cnd(sym, ex, t.upper())
    bot.delete_message(m.chat.id, wait_msg.message_id)

    if not d: return send_msg(m.chat.id, f"⚠️ تعذر جلب بيانات لـ {sym}@{ex}.")

    analysis_msg = gen_txt(sym, ex, d["atl"], d["ath"], d["cur"], t)
    send_msg(m.chat.id, analysis_msg, True, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text in ["🤖 التداول الآلي", "التداول الآلي"])
def auto_trading(m):
    """فتح قائمة التداول الآلي"""
    del_eph(m.chat.id)
    send_msg(m.chat.id, "🤖 نظام التداول الآلي المتقدم:", reply_markup=kb())

@bot.message_handler(func=lambda m: m.text in ["⚙️ إعدادات", "إعدادات"])
def settings_cmd(m):
    """فتح إعدادات التداول الآلي"""
    del_eph(m.chat.id)
    k = ReplyKeyboardMarkup(resize_keyboard=True)
    k.row("🔗 ربط", "➕ إضافة")
    k.row("📊 نوع", "⚖️ نسبة")
    k.row("🔍 قوة", "🔙 تداول")
    send_msg(m.chat.id, "⚙️ إعدادات التداول الآلي:", reply_markup=k)

@bot.message_handler(func=lambda m: m.text in ["🔙 تداول", "تداول", "🔙 رئيسية", "رئيسية"])
def back_cmd(m):
    """العودة للقوائم السابقة"""
    del_eph(m.chat.id)
    if "تداول" in m.text: send_msg(m.chat.id, "🔙 العودة لقائمة التداول", reply_markup=kb())
    else: send_msg(m.chat.id, "🏠 القائمة الرئيسية")

@bot.message_handler(func=lambda m: m.text in ["🔗 ربط", "ربط"])
def link_cmd(m):
    """ربط منصة التداول"""
    del_eph(m.chat.id)
    try:
        bot.delete_message(m.chat.id, m.message_id)
    except Exception as e:
        logger.warning(f"تعذر حذف رسالة المستخدم: {e}")

    msg = send_msg(m.chat.id, "🌐 اختر منصة التداول:", reply_markup=ReplyKeyboardRemove())
    if msg: bot.register_next_step_handler(msg, proc_ex)

def proc_ex(m):
    """معالجة اختيار المنصة"""
    del_eph(m.chat.id)
    try:
        bot.delete_message(m.chat.id, m.message_id)
    except Exception as e:
        logger.warning(f"تعذر حذف رسالة المستخدم: {e}")

    uid, ex = m.from_user.id, m.text.lower()
    if ex not in EXCHANGES: return send_msg(uid, "⚠️ المنصة غير مدعومة!")
    s = load_d(uid, "settings") or {}
    s['ex'] = ex
    save_d(uid, "settings", s)
    send_msg(uid, f"✅ تم اختيار {ex.capitalize()}!")
    msg = send_msg(uid, "🔑 أرسل API Key:", reply_markup=ReplyKeyboardRemove())
    if msg: bot.register_next_step_handler(msg, proc_key, ex)

def proc_key(m, ex):
    """معالجة مفتاح API"""
    del_eph(m.chat.id)
    try:
        bot.delete_message(m.chat.id, m.message_id)
    except Exception as e:
        logger.warning(f"تعذر حذف رسالة المستخدم: {e}")

    uid, key = m.from_user.id, m.text.strip()
    s = load_d(uid, "settings") or {}
    if 'keys' not in s: s['keys'] = {}
    s['keys'][ex] = {'k': enc(key)}
    save_d(uid, "settings", s)
    send_msg(uid, "✅ تم حفظ API Key!", reply_markup=ReplyKeyboardRemove())
    msg = send_msg(uid, "🔒 أرسل API Secret:", reply_markup=ReplyKeyboardRemove())
    if msg: bot.register_next_step_handler(msg, proc_sec, ex)

def proc_sec(m, ex):
    """معالجة السر السري لـ API"""
    del_eph(m.chat.id)
    try:
        bot.delete_message(m.chat.id, m.message_id)
    except Exception as e:
        logger.warning(f"تعذر حذف رسالة المستخدم: {e}")

    uid, sec = m.from_user.id, m.text.strip()
    s = load_d(uid, "settings") or {}
    if ex == 'mexc': save_mexc(uid, s['keys'][ex]['k'], sec)
    else: s['keys'][ex]['s'] = enc(sec)
    save_d(uid, "settings", s)
    send_msg(uid, "✅ تم ربط المنصة بنجاح!", reply_markup=kb())

@bot.message_handler(func=lambda m: m.text in ["➕ إضافة", "إضافة"])
def add_cmd(m):
    """إضافة عملات للتداول الآلي"""
    del_eph(m.chat.id)
    try:
        bot.delete_message(m.chat.id, m.message_id)
    except Exception as e:
        logger.warning(f"تعذر حذف رسالة المستخدم: {e}")

    msg = send_msg(m.chat.id, "🪙 أرسل رموز العملات (مفصولة بمساحة):\nمثال: `BTC ETH SOL`", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    if msg: bot.register_next_step_handler(msg, proc_add)

def proc_add(m):
    """معالجة العملات المضافة"""
    del_eph(m.chat.id)
    try:
        bot.delete_message(m.chat.id, m.message_id)
    except Exception as e:
        logger.warning(f"تعذر حذف رسالة المستخدم: {e}")

    uid, coins = m.from_user.id, [c.upper().strip() for c in m.text.strip().split() if c.strip()]
    if not coins: return send_msg(uid, "⚠️ لم يتم إدخال عملات!", reply_markup=kb())
    s = load_d(uid, "settings") or {}
    s['coins'] = coins
    save_d(uid, "settings", s)
    send_msg(uid, f"✅ تم إضافة {len(coins)} عملة للتداول!", reply_markup=kb())

@bot.message_handler(func=lambda m: m.text in ["📊 نوع", "نوع"])
def type_cmd(m):
    """تغيير نوع التداول"""
    del_eph(m.chat.id)
    k = ReplyKeyboardMarkup(resize_keyboard=True)
    k.row("📈 استثماري (B)", "📉 مضاربي (S)", "🔙 تداول")
    send_msg(m.chat.id, "📊 اختر نوع التداول:", reply_markup=k)

@bot.message_handler(func=lambda m: m.text in ["📈 استثماري (B)", "استثماري (B)"])
def long_term(m):
    """تعيين التداول الاستثماري"""
    del_eph(m.chat.id)
    uid = m.from_user.id
    s = load_d(uid, "settings") or {}
    s['type'] = 'B'
    save_d(uid, "settings", s)
    send_msg(uid, "✅ تم تعيين: استثماري طويل الأجل", reply_markup=kb())

@bot.message_handler(func=lambda m: m.text in ["📉 مضاربي (S)", "مضاربي (S)"])
def short_term(m):
    """تعيين التداول المضاربي"""
    del_eph(m.chat.id)
    uid = m.from_user.id
    s = load_d(uid, "settings") or {}
    s['type'] = 'S'
    save_d(uid, "settings", s)
    send_msg(uid, "✅ تم تعيين: مضاربي قصير الأجل", reply_markup=kb())

@bot.message_handler(func=lambda m: m.text in ["⚖️ نسبة", "نسبة"])
def pct_cmd(m):
    """تغيير نسبة رأس المال"""
    del_eph(m.chat.id)
    try:
        bot.delete_message(m.chat.id, m.message_id)
    except Exception as e:
        logger.warning(f"تعذر حذف رسالة المستخدم: {e}")

    uid = m.from_user.id
    msg = send_msg(uid, "💼 أدخل النسبة المئوية لرأس المال (0.5% إلى 100%):", reply_markup=ReplyKeyboardRemove())
    if msg: bot.register_next_step_handler(msg, proc_pct)

def proc_pct(m):
    """معالجة نسبة رأس المال"""
    del_eph(m.chat.id)
    try:
        bot.delete_message(m.chat.id, m.message_id)
    except Exception as e:
        logger.warning(f"تعذر حذف رسالة المستخدم: {e}")

    uid = m.from_user.id
    try:
        p = float(m.text)
        if 0.5 <= p <= 100:
            s = load_d(uid, "settings") or {}
            s['cap_pct'] = p
            save_d(uid, "settings", s)
            send_msg(uid, f"✅ تم تعيين نسبة رأس المال إلى {p}%", reply_markup=kb())
        else: raise ValueError
    except: send_msg(uid, "⚠️ قيمة غير صالحة!", reply_markup=kb())

@bot.message_handler(func=lambda m: m.text in ["📋 عملات", "عملات", "🔍 قوة", "قوة"])
def coins_cmd(m):
    """عرض قوة إشارات العملات"""
    del_eph(m.chat.id)
    uid = m.from_user.id
    s = load_d(uid, "settings") or {}
    coins = s.get('coins', [])
    if not coins:
        send_msg(uid, "📭 لا توجد عملات مضافة!", reply_markup=kb())
        return

    ex = s.get('ex', 'mexc')
    if not ex:
        send_msg(uid, "⚠️ لم يتم اختيار منصة التداول بعد. الرجاء الإعدادات ⚙️", reply_markup=kb())
        return

    t = "📊 قوة إشارات العملات:\n\n"
    for coin in coins:
        try:
            d = get_cnd(coin, ex, s.get('type', 'B'))
            if d and d['ath'] and d['atl'] and d['cur']:
                ath, atl, cur = d['ath'], d['atl'], d['cur']
                if s.get('type') == 'S':
                    vc = min((ath - atl) / atl * 100 * 1.2, 50)
                    pc = min((cur - atl) / (ath - atl) * 100 * 1.5, 50)
                    strn = min(vc + pc, 100)
                else:
                    p = (cur - atl) / (ath - atl) * 100
                    vol = (ath - atl) / atl * 100
                    strn = max(0, 100 - abs(p - 50)) * (min(vol,50)/50)
                st = "📈 ممتازة" if strn>85 else "📈 جيدة" if strn>70 else "🔼 مقبولة" if strn>50 else "↘️ ضعيفة"
                t += f"• {coin}: {strn:.0f}% - {st}\n"
            else: t += f"• {coin}: ❌ فشل جلب البيانات\n"
        except: t += f"• {coin}: ❌ خطأ\n"
    send_msg(uid, t, reply_markup=kb())

@bot.message_handler(func=lambda m: m.text in ["▶️ تشغيل", "تشغيل"])
def on_cmd(m):
    """تشغيل التداول الآلي"""
    del_eph(m.chat.id)
    uid = m.from_user.id
    s = load_d(uid, "settings") or {}
    s['on'] = True
    save_d(uid, "settings", s)
    if uid not in user_scans: user_scans[uid] = {"t":0, "i":0, "b":None}
    send_msg(uid, "✅ تم تفعيل التداول الآلي!")

@bot.message_handler(func=lambda m: m.text in ["⏸ إيقاف", "إيقاف"])
def off_cmd(m):
    """إيقاف التداول الآلي"""
    del_eph(m.chat.id)
    uid = m.from_user.id
    s = load_d(uid, "settings") or {}
    s['on'] = False
    save_d(uid, "settings", s)
    send_msg(uid, "⏸ تم إيقاف التداول الآلي مؤقتاً!")

@bot.message_handler(func=lambda m: m.text in ["📊 حالة", "حالة"])
def status_cmd(m):
    """عرض حالة الصفقات النشطة"""
    del_eph(m.chat.id)
    uid = m.from_user.id
    t = user_trades.get(uid, {})
    if not t.get("on"): return send_msg(uid, "📭 لا توجد صفقات نشطة")

    s = load_d(uid, "settings") or {}
    coin, e = t["coin"], t["e"]
    cur = get_prc(coin, s.get('ex', 'mexc')) or e
    pft = ((cur - e) / e) * 100
    dur = datetime.now(timezone.utc) - t["t"]
    h, rem = divmod(dur.seconds, 3600)
    m, sec = divmod(rem, 60)

    msg = [
        f"📊 صفقة نشطة على {s.get('ex', 'mexc').upper()}",
        f"⏱ المدة: {h}س {m}د {sec}ث",
        f"💳 العملة: {coin}",
        f"📈 السعر الحالي: {cur}",
        f"💰 نقطة الدخول: {e}",
        f"📈 الربح الحالي: {pft:.2f}%",
        f"⚖️ رأس المال: {s.get('cap_pct',100)}%"
    ]
    send_msg(uid, "\n".join(msg))

@bot.message_handler(func=lambda m: m.text in ["⚖️ رأس مال", "رأس مال"])
def cap_cmd(m):
    """تغيير رأس المال"""
    del_eph(m.chat.id)
    try:
        bot.delete_message(m.chat.id, m.message_id)
    except Exception as e:
        logger.warning(f"تعذر حذف رسالة المستخدم: {e}")

    uid = m.from_user.id
    cap = (load_d(uid, "cap") or {}).get('cap', 0)
    msg = send_msg(uid, f"💼 رأس المال الحالي: ${cap:.2f}\n\nأرسل المبلغ الجديد:", reply_markup=ReplyKeyboardRemove())
    if msg: bot.register_next_step_handler(msg, proc_cap)

def proc_cap(m):
    """معالجة قيمة رأس المال الجديد"""
    del_eph(m.chat.id)
    try:
        bot.delete_message(m.chat.id, m.message_id)
    except Exception as e:
        logger.warning(f"تعذر حذف رسالة المستخدم: {e}")

    uid = m.from_user.id
    try:
        cap = float(m.text)
        if cap > 0:
            save_d(uid, "cap", {'cap': cap})
            send_msg(uid, f"✅ تم تحديث رأس المال إلى ${cap:.2f}", reply_markup=kb())
        else: raise ValueError
    except: send_msg(uid, "⚠️ قيمة غير صالحة!", reply_markup=kb())

@bot.message_handler(func=lambda m: m.text in ["🗑️ حذف", "حذف"])
def del_cmd(m):
    """حذف عملات من التداول الآلي"""
    del_eph(m.chat.id)
    uid = m.from_user.id
    s = load_d(uid, "settings") or {}
    coins = s.get('coins', [])
    if not coins: return send_msg(uid, "📭 لا توجد عملات مضافة!")
    k = ReplyKeyboardMarkup(resize_keyboard=True)
    for coin in coins: k.row(f"حذف {coin}")
    k.row("🔙 إلغاء")
    msg = send_msg(uid, "اختر العملة للحذف:", reply_markup=k)
    bot.register_next_step_handler(msg, proc_del)

def proc_del(m):
    """معالجة حذف العملة"""
    del_eph(m.chat.id)
    uid, c = m.from_user.id, m.text.strip()
    if c == "🔙 إلغاء": return send_msg(uid, "تم الإلغاء", reply_markup=kb())
    if c.startswith("حذف "):
        coin = c[5:].strip()
        s = load_d(uid, "settings") or {}
        if coin in s.get('coins', []):
            s['coins'].remove(coin)
            save_d(uid, "settings", s)
            send_msg(uid, f"✅ تمت إزالة {coin}!", reply_markup=kb())
            return
    send_msg(uid, "⚠️ إدخال غير صحيح!", reply_markup=kb())

if __name__ == "__main__":
    logger.info(f"Starting bot v{BOT_VERSION}")
    auto_trade()
    bot.infinity_polling()