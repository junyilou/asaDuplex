import logging, os

def disMarkdown(text):
	temp = text
	signs = "\\|_{}[]()#+-.!=<>"
	for s in signs:
		temp = temp.replace(s, f"\\{s}")
	return temp

def setLogger(level, name):
	if os.path.isdir('logs'):
		logging.basicConfig(
			filename = f"logs/{name}.log",
			format = '[%(asctime)s %(levelname)s] %(message)s',
			level = level, filemode = 'a', datefmt = '%F %T')
	else:
		logging.basicConfig(
			format = '[%(process)d %(asctime)s %(levelname)s] %(message)s',
			level = level, datefmt = '%T')

asaVersion = "5.12.0"
asaAgent = ".".join(asaVersion.split(".")[:2])
asaHeaders = {
	"User-Agent": f"ASA/{asaAgent} (iPhone) ss/3.00",
	"x-ma-pcmh":  f"REL-{asaVersion}",
	"X-MALang":   "zh-CN",
	"X-Apple-I-TimeZone": "GMT+8",
	"X-Apple-I-Locale":   "zh_CN",
	"X-MMe-Client-Info": f"<iPhone13,2> <iPhone OS;14.3;18C66> <com.apple.AuthKit/1 (com.apple.store.Jolly/{asaVersion})>",
	"X-DeviceConfiguration":  f"ss=3.00;dim=1170x2532;m=iPhone;v=iPhone13,2;vv={asaAgent};sv=14.3"}
asaNation = {'🇺🇸': 'a/us', '🇨🇳': 'p/cn', '🇬🇧': 'e/uk', '🇨🇦': 'a/ca', '🇦🇺': 'p/au', '🇫🇷': 'e/fr', 
	'🇮🇹': 'e/it', '🇩🇪': 'e/de', '🇪🇸': 'e/es', '🇯🇵': 'j/jp', '🇨🇭': 'e/ch-de', '🇦🇪': 'e/ae', '🇳🇱': 'e/nl', 
	'🇸🇪': 'e/se', '🇧🇷': 'a/br', '🇹🇷': 'e/tr', '🇸🇬': 'p/sg', '🇲🇽': 'a/mx', '🇦🇹': 'e/at', '🇧🇪': 'e/be-fr', 
	'🇰🇷': 'p/kr', '🇹🇭': 'p/th-en', '🇭🇰': 'p/hk-zh', '🇹🇼': 'p/tw'}

dieterURL = lambda sid: f"https://rtlimages.apple.com/cmc/dieter/store/16_9/R{sid}.png?\
resize=2880:1612&output-format=jpg&output-quality=90&interpolation=progressive-bicubic"

userAgent = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6)\
AppleWebKit/605.1.15(KHTML, like Gecko)Version/14.0.2 Safari/605.1.15"}

webNation = {**dict([(i[0], i[1][1:4]) for i in asaNation.items()]), 
	"🇺🇸": '', "🇨🇳": '.cn', "🇨🇭": "/chde", "🇧🇪": "/befr", "TW": "/tw", '🇲🇴': '/mo'} # for /retail
storeNation = {**webNation, "🇨🇭": "/ch-de", "🇧🇪": "/be-fr"} # for /shop

partSample = {'🇺🇸': 'AM', '🇨🇳': 'FE', '🇬🇧': 'ZM', '🇨🇦': 'AM', '🇦🇺': 'FE', '🇫🇷': 'ZM', 
	'🇮🇹': 'ZM', '🇩🇪': 'ZM', '🇪🇸': 'ZM', '🇯🇵': 'FE', '🇳🇱': 'ZM', 
	'🇸🇪': 'ZM', '🇸🇬': 'FE', '🇦🇹': 'ZM', 
	'🇰🇷': 'FE', '🇹🇭': 'FE', '🇭🇰': 'FE', '🇹🇼': 'FE'}
partRuleFull = "([FGHMNPS][0-9A-Z]{3}[0-9][A-Z]{1,2}/[A-Z])"
partRuleCheck = "([FGHMNPS][0-9A-Z]{3}[0-9]([A-Z]{1,2}/[A-Z]))"

DIFFhead = """
<!DOCTYPE html>

<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DIFF HEAD</title>
</head>

<body><pre><code>\n"""
DIFFfoot = "</code></pre></body></html>"

editStart = "### *** EDIT START *** ###\n"
editEnd   = "\n### *** EDIT  END  *** ###"

dayOfWeekCHN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
dayOfWeekENG = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

orderDict = {
	'PLACED': '订单已下达', 'PROCESSING': '正在处理订单', 'COMPLETE': '订单已完成',
	'PREPARED_FOR_SHIPMENT': '准备发货', 'SHIPPED': '已发货', 'DELIVERED': '已送达', 
	'RETURN_STARTED': '已发起退货', 'RETURN_RECEIVED': '退货已收到', 'REFUND_INITIATED': '退货完成', 
	'READY_FOR_COURIER': '等待承运商取货', 'PICKEDUP_BY_COURIER': '承运商已取货', 
	'SHIPPED_TO_YOU': '已发货', 'DELIVERED_TO_YOU': '已送达', 'SHIPPED_TO_APPLE': '已送至 Apple', 
	'TRADEIN_COMPLETE': '折抵换购完成', 'RECEIVED_AT_APPLE': 'Apple 已收货', 
	'READY_FOR_PICKUP': '随时可取', 'PICKED_UP': '已取货', 'SHIPPING_TO_STORE': '正在送货到零售店', 
	'CHECKIN_TODAY': '今日办理登记', 'EMAIL_SENT': '已发送电子邮件', 'ELECTRONICALLY_DELIVERED': '已经以电子方式发送', 
	'PAYMENT_RECEIVED': '已收到付款', 'ORDER_IN_PROGRESS': '订单处理中', 'OUT_FOR_DELIVERY': '正在派送', 
	'ARRIVING_SOON': '即将送达', 'DELIVERS': '送达日期', 
	'TRADEUP_SHIPPED_TO_YOU': '已通知承运商', 'TRADEUP_RECEIVED_BY_PARTNER': '折抵服务合作伙伴已收到设备', 'TRADEUP_COMPLETE': '折抵换购完成', 
	'RECEIVED_BY_CARRIER': '承运商已揽收', 'RECEIVED_BY_APPLE': 'Apple 已收货', 
	'SHIPPING_TO_PICKUP_POINT': '正在运往取货点', 'PREPARING_FOR_DISPATCH': '正在准备派送', 'DISPATCHED': '已派送',
	'PAYMENT_DUE_STORED_ORDER': '等待付款', 'PAYMENT_DUE': '等待付款', "CANCELED": "已取消", 
	"PAYMENT_EXPIRED": "订单已过期", "PAYMENT_EXPIRED_STORED_ORDER": "订单已过期"}
completeStatus = [
	"COMPLETE", "TRADEIN_COMPLETE", "TRADEUP_COMPLETE", "DELIVERED_TO_YOU", "DELIVERED",
	"REFUND_INITIATED", "PICKED_UP", "EMAIL_SENT", "ELECTRONICALLY_DELIVERED", "CANCELED", "PAYMENT_EXPIRED"]

RecruitState = ["土耳其", "阿联酋", "英国", "德国", "台湾", "美国", 
"墨西哥", "瑞士", "比利时", "荷兰", "西班牙", "香港", "瑞典", "中国", 
"法国", "澳大利亚", "意大利", "澳门", "巴西", "日本", "韩国", "加拿大", "奥地利"]
RecruitEmoji = ["🇹🇷", "🇦🇪", "🇬🇧", "🇩🇪", "🇹🇼", "🇺🇸", 
"🇲🇽","🇨🇭", "🇧🇪", "🇳🇱", "🇪🇸", "🇭🇰", "🇸🇪", "🇨🇳", 
"🇫🇷", "🇦🇺", "🇮🇹", "🇲🇴", "🇧🇷", "🇯🇵", "🇰🇷", "🇨🇦", "🇦🇹"]
RecruitCode  = [8164, 8225, 8145, 8043, 8311, 8158, 
8297, 8017, 8251, 8119, 8056, 8082, 8132, 8030, 
8069, 7991, 8095, 8282, 8176, 8107, 8326, 8004, 8333]
