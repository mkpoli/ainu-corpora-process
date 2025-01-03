import csv
from io import StringIO


_DATA = """aep	aepi		食
aep	epi	epihi	食
ak	aki	akihi	弟
am	ami	amihi	爪
amip	mipi	mipihi	服
amunin	amunini	amuninihi	腕
ancikar	ancikari	ancikarihi	夜
asam	asama	asamaha	底
askepet	askepeci	askepecihi	指
askekursut	askekursutu	askekursutuhu	指の付け根
asur	asuru	asuruhu	噂
at	atu	atuhu	紐
atay	ataye	atayehe	値打ち
atkoci	atkocike		尾びれ
atpa	atpake	atpakehe	始め
atupok	atupoki	atupokihi	脇の下
ay	aye	ayehe	矢
car	caro	caroho	口
cikas	cikasi	cikasihi	心張り棒
cikir	cikiri	cikirihi	足
cipuy	cipuye	cipuyehe	陰茎の穴・女性器の陰門
ciyay	ciyaye	ciyayehe	栓
corpok	corpokike	corpokikehe	下
corpok	corpokke	corpokkehe	下
cup	cupi	cupihi	女の腹
cupkes	cupkesi	cupkesihi	女の下腹
eepak	eepaki	eepakihi	次
eepak	eepakke	eepakkehe	次
ekas	ekasi	ekasihi	祖父
enka	enkasi	enkasike	上の方
enka	enkasike	enkasikehe	上の方
enkip	enkipi	enkipihi	陰部
ep	epi	epihi	餌
epuy	epuyke	epuykehe	実
etok	etoko	etokoho	先
etor	etori	etorihi	鼻糞
etu	etu	etuhu	鼻
etuikkew	etuikkewe	etuikkewehe	鼻筋
etupsik	etupsike		先端
etupuy	etupuyke		鼻孔
eturus	eturusi	eturusihi	鼻面
ham	hamu	hamuhu	葉
hankapuy	hankapuye	hankapuyehe	臍
hanku	hanku	hankuhu	臍
harkisam	harkisama		左側
harkitek	harkiteke	harkitekehe	左手
haruramat	haruramatu	haruramatuhu	食糧の魂
haw	hawe	hawehe	声
heserekut	heserekuci	heserekucihi	気管
hon	honi	honihi	腹
honkes	honkese	honkesehe	下腹
hontom	hontomo	hontomoho	途中
hum	humi	humihi	音
hunakor	hunakoro		何処
hurkap	hurkapu	hurkapuhu	動物の死骸
ikir	ikiri	ikirihi	集まり
ikkew	ikkewe	ikkewehe	腰
ikusakanram	ikusakanrami	ikusakanramihi	悪い酒癖
ikuynimak	ikuynimaki	ikuynimakihi	奥歯
imak	imaki	imakihi	歯
imak	imakake	imakakehe	向こう
inawsantek	inawsanteke	inawsantekehe	木幣を捧げる子孫
inay	inaye	inayehe	尻の割れ目
ipe	ipe	ipehe	食
iperekut	iperekuci	iperekucihi	食道
ipor	iporo	iporoho	顔色
irwak	irwaki	irwakihi	兄弟姉妹
ka	ka	kaha	糸
ka	kasi	kasihi	上
ka	kasike	kasikehe	上
ka	kaske	kaskehe	上
kam	kami	kamihi	肉
kamka	kamkasi	kamkasike	肌
kankap	kankapu	kankapuhu	表皮
kannanotkew	kannanotkewe	kannanotkewehe	上顎
kannapatoy	kannapatoye	kannapatoyehe	上唇
kanpar	kanparo	kanparoho	口先
kap	kapu	kapuhu	皮
kaparkam	kaparkami	kaparkamihi	肋膜
karku	karku	karkuhu	甥
kaskamuy	kaskamuye		憑神
kat	katu	katuhu	恰好
katcam	katcama		気配
katuyemimak	katuyemimaki	katuyemimakihi	犬歯
kem	kemi	kemihi	血
kem	kemi	kemihi	飢饉
kemorit	kemorici	kemoricihi	血管
kema	kema	kemaha	脚
kepuspe	kepuspe	kepuspehe	鞘
ker	keri	kerihi	靴
kesup	kesupi	kesupihi	踵
kesupasam	kesupasama	kesupasamaha	踵裏
kew	kewe	kewehe	体
kewsut	kewsutu	kewsutuhu	おじ
kewtum	kewtumu	kewtumuhu	心
kik	kiki		守り
kim	kimke	kimkehe	山
kinop	kinopi	kinopihi	肝臓・腎臓
kip	kipi	kipihi	髪の生え際
kiraw	kirawe	kirawehe	角
kirkew	kirkewe	kirkewehe	足の骨
kiror	kiroro	kiroroho	大力
kisanrap	kisanrapu	kisanrapuhu	耳朶
kisanrit	kisanritu	kisanrituhu	耳筋
kisar	kisara	kisaraha	耳
kisarpuy	kisarpuyke	kisarpuykehe	耳孔
kisattur	kisatturi	kisatturihi	耳垢
kitay	kitayke	kitaykehe	頂上
kiyutur	kiyuturu	kiyuturuhu	網目
ko	ko	koho	粉
kokkasapa	kokkasapa	kokkasapaha	膝
kokow	kokowe	kokowehe	婿
kosmat	kosmaci	kosmacihi	嫁
kot	koci	kocihi	窪み
kotan	kotanu	kotanuhu	村
kotca	kotcake	kotcakehe	前
kotkarku	kotkarku	kotkarkuhu	姪
kotor	kotoro	kotoroho	面
kotpar	kotparu	kotparuhu	喉元
kotpok	kotpoki	kotpokke	直前
koyka	koykasi	koykasike	東の方
koyka	koykaske	koykaskehe	東の方
koypok		koypokke	西の方
ku	ku	kuhu	弓
ku	ku	kuwehe	アマッポ
kukew	kukewe	kukewehe	鎖骨
kunnesiknum	kunnesiknumi	kunnesiknumihi	黒目
kur	kuri	kurihi	影
kura	kura	kuraha	鞍
kurka	kurkasi	kurkasike	上面一帯
kurka	kurkasike	kurkasikehe	上面一帯
kursut	kursutu	kursutuhu	根元
kut	kuci	kucihi	帯
kutcam	kutcama		声音
kuttom	kuttomo	kuttomoho	喉
kuwa	kuwa	kuwaha	杖・墓標
mak	makke		奥
mat	maci	macihi	女
matak	mataki	matakihi	妹（姉から見た）
matapa	matapa	matapaha	妹（兄から見た）
matkarku	matkarku	matkarkuhu	姪
matnepo	matnepo	matnepoho	娘
maw	mawe	mawehe	息吹
mawka	mawkasi	mawkaske	風上
may	maye	mayehe	響き
mecip	mecipi	mecipihi	盆の窪
merit	merici	mericihi	首筋
mesas	mesasi	mesasihi	鬣
mim	mimi	mimihi	魚肉
mimak	mimaki	mimakihi	歯
mimakutur	mimakuturu	mimakuturuhu	歯の間
mippo	mippo	mippoho	孫
mokrap	mokrapu	mokrapuhu	胸鰭
monpok	monpoki	monpokihi	直ぐ下
montum	montumu	montumuhu	体調
mor	moru	moruhu	耳の前の毛
mur	muru	muruhu	糠
nan	nanu	nanuhu	顔
nankap	nankapu	nankapuhu	顔の皮膚
nayetok	nayetoko	nayetokoho	沢の水源
nayiwor	nayiwori		沢の中
netopa	netopake	netopakehe	胴体
niik	niiki	niikihi	切った薪
nikor	nikoro		包まれる中
nikotor	nikotoro	nikotoroho	口蓋
nimak	nimaki	nimakihi	歯
nimar	nimara	nimaraha	半数
ninkew	ninkewe	ninkewehe	背骨
nip	nipi	nipihi	柄
nipek	nipeki	nipekihi	輝き
nippo	nippo	nippoho	孫
nirus	nirusi	nirusihi	顰めっ面
nisap	nisapi	nisapihi	脛
nisikay	nisikaye	nisikayehe	木の節
nisut	nisutu	nisutuhu	歯茎
nit	nici	nicihi	柄・茎
nitek	niteke	nitekehe	枝
nítumam	nítumama	nítumamaha	幹
niyutur	niyuturke		歯の間
nok	noki	nokihi	鳥卵
nokpi	nokpiye	nokpiyehe	睾丸
non	noni	nonihi	唾
noski	noskike	noskikehe	真ん中
not	noci	nocihi	顎
notahuy	notahuye	notahuyehe	頬
notak	notaku	notakuhu	刃
notakam	notakami	notakamihi	頬
notarap	notarapu	notarapuhu	魚の頬骨
notkew	notkewe	notkewehe	下顎
notkir	notkiri	notkirihi	顎先
noyap	noyapi	noyapihi	横顔
num	numi	numihi	粒
nupe	nupe	nupehe	涙
oarsik	oarsiki	oarsikihi	片目
oatcikir	oatcikiri	oatcikirihi	片足
oattap	oattapu	oattapuhu	片肩
oattapcikir	oattapcikiri	oattapcikirihi	片方の前足
oattapsut	oattapsutu	oattapsutuhu	片肩
oattek	oattekke	oattekkehe	片手
ois	oisi	oisihi	尾羽
oka	okake	okakehe	後
okka	okkasi		上
okkew	okkewe	okkewehe	襟首
okrit	okrici	okricihi	襟筋
oksut	oksutu	oksutuhu	襟足
oksuy	oksuye	oksuyehe	襟元
om	omi	omihi	大腿
omkursut	omkursutu	omkursutuhu	腿の付け根
ona	ona	onaha	父親
onnay	onnayke	onnaykehe	内
or	oro	oroke	場所
or	orke	orkehe	場所
osmak	osmake	osmakehe	後ろ
osor	osoro	osoroho	尻
osorkam	osorkami	osorkamihi	尻べた
osorpuy	osorpuye	osorpuyehe	肛門
oske	ossike	ossikehe	中
ot	oci	ocihi	棺莚
otop	otopi	otopihi	髪
oka	okake	okakehe	後
ous	osui	osuke	麓
aoypep	oypepi	oypepihi	食器
paenrum	paenrumi	paenrumihi	口の先端
pahaw	pahawe	pahawehe	噂
pakisar	pakisara	pakisaraha	口角
pana	panake	panakehe	川下
panikkew	panikkewe	panikkewehe	腰下
par	paro	paroho	口
paratek	parateke	paratekehe	手首より先
parir	pariri	paririhi	煙
parunpe	parunpe	parunpehe	舌
parur	parurke	parurkehe	縁
paspas	paspasi	paspasihi	消し炭
patoy	patoye	patoyehe	唇
paypor	payporo	payporoho	唇色
pe	pe	pehe	水気
pena	penake		川上
penram	penramu	penramuhu	胸
penrekut	penrekuci	penrekucihi	首の前側
petetok	petetoko	petetokoho	水源地
petutur	petuturu	petuturuhu	川と川の間
pi	piye	piyehe	小石
pir	piri	pirihi	傷
po	po	poho	子
pokinkap	pokinkapu	pokinkapuhu	内皮
pokisir	pokisirke		股下
poksapa	poksapa	poksapaha	陰茎亀頭
pone	pone	ponehe	骨
ponmat	ponmaci	ponmacihi	妾
punkar	punkari	punkarihi	蔓
pus	pusi	pusihi	穂
put	putu	putuhu	河口
puta	puta	putaha	蓋
puy	puye	puyehe	穴
raciw	raciwe	raciwehe	眉形
ram	ramu	ramuhu	心
ramat	ramatu	ramatuhu	魂
ramat	ramaci	ramacihi	魂
ramram	ramrami	ramramihi	鱗
rantupep	rantupepi	rantupepihi	顎紐
rap	rapu	rapuhu	羽
rapok	rapoki	rapokke	途中
rar	raru	raruhu	眉
rarutur	raruturu	raruturuhu	眉間
rat	raci	racihi	痰
raykew	raykewe	raykewehe	屍体
re	re	rehe	名
rek	reki	rekihi	髭
rekkisar	rekkisara	rekkisaraha	揉み上げ
rekut	rekuci	rekucihi	喉
reprepke	repkehe		沖
rerar	rerari	rerarihi	乳房
retarsiknum	retarsiknumi	retarsiknumihi	白目
rewka	rewkasi	rewkaske	曲がった上
rewkurka	rewkurkasi		曲がった上面一帯
rewkurpok	rewkurpoki		曲がった下面一帯
rit	rici	ricihi	筋
ror	rorke	rorkehe	上座
ru	ruwe	ruwehe	道
rukum	rukumi	rukumihi	短棒
runum	runumi	runumihi	豆
runumnep	runumnepi	runumnepihi	豆
rup	rupi	rupihi	列群
rur	ruri	rurihi	汁
rus	rusi	rusihi	毛皮
ruwoka	ruwokake		死後
ruwor	ruworo		低地
sa	sa	saha	姉
sa	sake	sakehe	節
sakanram	sakanrami	sakanramihi	短気
saksamaw	saksamawe	saksamawehe	悪臭
sam	sama	samaha	側
sam	samake	samakehe	側
san	sani		子孫
sankemat	sankemaci	sankemacihi	正妻
sanpe	sanpe	sanpehe	心臓
sanpepok	sanpepoki		鳩尾
santek	santeke	santekehe	世継ぎ
sapa	sapa	sapaha	頭
saparus	saparusi	saparusihi	剥けた頭皮
sapikir	sapikiri	sapikirihi	血統
sar	sara	saraha	尾
sar	sari	sarihi	葦原
satairwak	satairwaki	satairwakihi	従兄弟姉妹
say	saye	sayehe	首飾り
say	sayke	saykehe	群
sempir	sempiri	sempirke	陰
ser	seri	serihi	布幅
ser	sere	serke	部分
sermak	sermaka	sermakaha	背後
setur	seturu	seturuhu	背中
sik	siki	sikihi	目
sikay	sikaye	sikayehe	目釘
sikkap	sikkapu	sikkapuhu	瞼
sikkes	sikkese	sikkesehe	目尻
siknum	siknumi	siknumihi	目玉
sikokes	sikokese	sikokesehe	目尻
sikpuy	sikpuye	sikpuyehe	目元
sikramat	sikramaci	sikramacihi	瞳
sikrap	sikrapu	sikrapuhu	睫毛
simontek	simonteke	simontekehe	右手
símoysam	símoysama		右側
sinrit	sinrici	sinricihi	根・先祖
sirka	sirkasi	sirkaske	地上
sirpok	sirpoki	sirpokke	布裏
sittokew	sittokewe	sittokewehe	肘
sittok	sittoki	sittokihi	肘
siyetok	siyetoko	siyetokoho	自分の前方
siyosmak	siyosmake		自分の背後
sos	sosi	sosihi	薄片
sowsut	sowsutu	sowsutuhu	隅
soy	soyke	soykehe	外
soyna	soynake		外側
sum	sumi	sumihi	油脂
sumaw	sumawe	sumawehe	殺した熊
sut	suci	sucihi	祖母
sut	sutu	sutuhu	根元
tapcikir	tapcikiri	tapcikirihi	前足
tapka	tapkasi		頂上
tapsut	tapsutu	tapsutuhu	肩
tas	tasu		呼気
tek	teke	tekehe	手
tekkotor	tekkotoro	tekkotoroho	掌
tekmekka	tekmekkasi		手の甲側
tekrukot	tekrukoci	tekrukocihi	手形
teksam	teksama	teksamaha	横
tektuypok	tektuypoki		掌側
tekukot	tekukoci	tekukocihi	手首
tem	temi	temihi	手の長さ
temsut	temsutu	temsutuhu	腕の付け根
ter	teri	terihi	粘液
to	to	toho	昼間
tokuy	tokuye	tokuyehe	親友
tononmimak	tononmimaki	tononmimakihi	前歯
tottonum	tottonumi	tottonumihi	乳首
tom	tomo		中程
tum	tumu	tumuke	中
tum	tumuke	tumukehe	中
tum	tumi	tumihi	力
tumam	tumama	tumamaha	胴
tupep	tupepi	tupepihi	顎紐
tur	turi	turihi	垢
tures	turesi	turesihi	妹（兄から見た）
tus	tusi	tusihi	妾（本妻から見た）
tusatuypok	tusatuypoki		袖下
tuy	tuye	tuyehe	魚腸
tuyka	tuykasi	tuykaske	上端
ukowtur	ukowturu	ukowturuhu	間
unarpe	unarpe	unarpehe	おば
uni	uni	unihi	家
unu	unu	unuhu	母親
up	upi	upihi	白子
upsor	upsoro	upsoroho	懐
ure	ure	urehe	足
ureous	ureousi	ureousihi	足元
ureasam	ureasama	ureasamaha	足の裏
urekot	urekoci	urekocihi	足跡
urekotor	urekotoro	urekotoroho	足の裏
uremekka	uremekkasi		足の甲側
urencikir	urencikiri	urencikirihi	両足
urenpiskan	urenpiskani	urenpiskanike	両側
urentapcikir	urentapcikiri	urentapcikirihi	両前足
urentek	urenteki	urentekihi	両手
urepet	urepeci	urepecihi	足指
usis	usisi	usisihi	蹄
utar	utari	utarihi	人々
utorsam	utorsama		脇
utur	uturu	uturuke	間
utur	uturke	uturkehe	間
útur	úturu	úturuke	下座
útur	úturke	úturkehe	下座
wata	wata	wataha	綿
ya	yake		陸地
yarpok	yarpokke		脇
yatupok	yatupoki	yatupokihi	脇の下
yatupok	yatupokke		脇の下
ye	ye	yehe	膿
yomtekkam	yomtekkami	yomtekkamihi	腿裏
yorpuy	yorpuye	yorpuyehe	肛門
yukram	yukrami	yukramihi	肺
yup	yupi	yupihi	兄"""


with StringIO(_DATA) as f:
    possessives: list[tuple[str, str, str]] = [
        (row[0], row[1], row[2]) for row in csv.reader(f, delimiter="\t")
    ]
