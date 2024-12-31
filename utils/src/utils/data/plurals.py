import csv
from io import StringIO


_DATA = """a	rok	座る	自動詞
a	rok	～した	助動詞
an	oka	居る	自動詞
aan	rokoka	～したのだった	助動詞
ahun	ahup	入る	自動詞
ahunke	ahupte	～を入れる	他動詞
ani	anpa	～を手に持つ	他動詞
arikiki	arikikpa	頑張る	自動詞
arpa	paye	行く	自動詞
as	roskiro	立つ	自動詞
asi	roski	～を立てる	他動詞
asin	asip	出る	自動詞
aske uk	aske uyna	～を招待する	連他動詞
aste	roskire	～を立たせる	他動詞
cari	carpa	～を散らす	他動詞
catcari	catcarpa	～を散播く	他動詞
cipekusa	cipekuspa	～を船で運ぶ	他動詞
cupu	cuppa	～を丸める	他動詞
earpa	epaye	～しに行く	他動詞
ehoyupu	ehoyuppa	～を持って走る	他動詞
ek	arki	来る	自動詞
ekiroroan	ekirorooka	～を面白く思う	他動詞
ekte	arkire	～を来させる	他動詞
emakaas	emakaroski	立ち止まる	自動詞
eramasu	eramaspa	～を気に入る	他動詞
eramuan	eramuoka	～が解る	他動詞
esiyetaye	esiyetaypa	～を引き寄せる	他動詞
etaye	etaypa	～を引く	他動詞
etemkorani	etemkoranpa	～を両腕で持ち運ぶ	他動詞
etuye	etuypa	～の先を切り揃える	他動詞
ewkohawpuni	ewkohawpunpa	～のことで騒ぐ	自動詞
eyaykosiramsuye	eyaykosiramsuypa	～を考える	他動詞
hawean	haweoka	言う	自動詞
hecawe	hecawpa	解れる	自動詞
hecirasa	heciraspa	咲く	自動詞
hekote	hekotpa	～の方へ向く	他動詞
hemesu	hemespa	上る	自動詞
henoye	henoypa	曲がる	自動詞
hetuku	hetukpa	顔を出す	自動詞
hopuni	hopunpa	起きる	自動詞
hopunire	hopunpare	～を起こす	他動詞
horari	horarpa	住む	自動詞
horipi	horippa	踊る	自動詞
hosari	hosarpa	振り返る	自動詞
hosipi	hosippa	帰る	自動詞
hosipire	hosippare	～を返す	他動詞
hotuye	hotuyepa	呼ばわる	自動詞
hoyupu	hoyuppa	走る	自動詞
hoyupure	hoyuppare	～を走らせる	他動詞
huraye	huraypa	～を洗う	他動詞
ihuraye	ihuraypa	洗濯する	他動詞
ikoahun	ikoahup	冒険して入る	自動詞
ineap	inerokpe	どうしたものか	感動詞
inukuri	inukurpa	体が自由に動かない	自動詞
itasa	itaspa	交代する	自動詞
kapa	kappa	～を平にする	他動詞
kaye	kaypa	～を折る	他動詞
kohemesu	kohemespa	～に登る	他動詞
koykutasa	koykutaspa	～に招かれる	他動詞
komo	kompa	～を折り曲げる	他動詞
kopuni	kopunpa	～に～を供する	複他動詞
korototo	korototpa	～を粉々にする	他動詞
koruyruye	koruyruypa	～に握手しする	他動詞
kouk	kouyna	～から～を奪う	複他動詞
koypuni	koypunpa	～に食べ物を供する	他動詞
kucasanke	kucasapte	狩小屋から村へ帰る	自動詞
kusa	kuspa	～を船で川を渡す	他動詞
mesu	mespa	～をもぎ取る	他動詞
móno a	mono rok	下に座る	自動詞
néa	nérok	例の	連体詞
nini	ninpa	～を引き摺る	他動詞
noye	noypa	～を撚る	他動詞
nuwe koan	nuwe kooka	～が沢山捕れる	連他動詞
numkoekomo	numkoekompa	～を取り囲む	他動詞
nuwe	nupa	～を掃く	他動詞
oarpa	opaye	～に行く	他動詞
oek	oarki	～から来る	他動詞
ohetu	ohetpa	～を吐き出す	他動詞
okere	okerpa	～を終える	他動詞
okere	okerpa	～し終わる	助動詞
okewe	okewpa	～を追い出す	他動詞
oma	o	～に位置する	他動詞
oman	paye	行く	自動詞
omanan	payoka	歩き回る	自動詞
onumposo	onumpospa	生き残る	自動詞
oputuye	oputuypa	～を押す	他動詞
osinritkomewe	osinritkomewpa	～を根刮ぎ倒す	他動詞
osiraye	osiraypa	～に足を運ぶ	他動詞
osura	osurpa	～を投げ捨てる	他動詞
otuye	otuypa	～を根元から刈る	他動詞
ouri	ourpa	～を掘る	他動詞
paru	parpa	～を煽ぐ	他動詞
petu	petpa	～を細かく裂く	他動詞
piru	pirpa	～を拭く	他動詞
puni	punpa	～を持ち上げる	他動詞
puskosanu	puskosanpa	弾けた音がする	自動詞
ramuan	ramuoka	思う	自動詞
ramuan	ramuoka	賢い	自動詞
ran	rap	降りる	自動詞
ranke	rapte	～を降ろす	他動詞
rari	rarpa	～を押えつける	他動詞
raye	raypa	～を行かせる	他動詞
rayke	ronnu	～を殺す	他動詞
resu	respa	～を育てる	他動詞
rewe	rewpa	～を曲げる	他動詞
rewsian	rewsioka	一晩泊まる	自動詞
rikin	rikip	登る	自動詞
rikinka	rikinkpa	～を上げる	他動詞
rise	rispa	～を毟る	他動詞
ruki	rukpa	～を飲み込む	他動詞
san	sap	下る	自動詞
sánasanke	sánasapte	～を出す	他動詞
sanke	sapte	～を出す	他動詞
sikiru	sikirpa	～へ向く	他動詞
simakoraye	simakoraypa	暇を取る	自動詞
sinewe	sinewpa	遊びに訪問する	自動詞
sipirasa	sipiraspa	広がる	自動詞
sipuni	sipunpa	持ち上がる	自動詞
siruskosanu	siruskosanpa	ぱっと消えて真っ暗になる	完全動詞
siyetaye	siyetaypa	～を引っ込む	自動詞
siyupu	siyuppa	締まる	自動詞
soso	sospa	～を剥がす	他動詞
soye	soypa	～を抉る	他動詞
sóyene	sóyenpa	外に出る	自動詞
soyne	sóyonpa	外に出る	自動詞
suwe	súpa	～を煮る	他動詞
taan	taoká	この	連体詞
tapan	tapoká	この	連体詞
toan	tooká	あの	連体詞
tomotarusi	tomotarusipa	～をを荷縄で背負う	他動詞
turi	turpa	～を伸ばす	他動詞
tuye	tuypa	～を切る	他動詞
uhekote	uhekotpa	一緒に暮らす	自動詞
uk	uyna	～を取る	他動詞
ukouk	ukouyna	～を奪い合う	他動詞
ukoyupu	ukoyuppa	～を締める	他動詞
úse anu	úse ári	～を取り出す	他動詞
uskosanu	uskosanpa	ぱっと消える	自動詞
utasare	utasarepa	～を取り変える	他動詞
uuste	uuspare	～を残さず伝える	他動詞
uwekari	uwekarpa	両方から寄ってくる	自動詞
uwekarire	uwekarpare	～を寄せ集める	他動詞
uwekohopi	uwekohoppa	分かれる	自動詞
uwomare	uwomarpare	～を集める	他動詞
yaku	yakpa	～を潰す	他動詞
yakyaku	yakyakpa	～を何回も潰す	他動詞
yan	yap	陸に上がる	自動詞
yasa	yaspa	～を裂く	他動詞
yayhetukure	yayhetukpare	自分で成長する	自動詞
yayosirkonoye	yayosirkonoypa	引き籠もる	自動詞
yupu	yuppa	～を締める	他動詞"""


def get_valency(verb_type: str) -> int:
    return {
        "完全動詞": 0,
        "連他動詞": 2,
        "複他動詞": 3,
        "他動詞": 2,
        "自動詞": 1,
    }[verb_type]


with StringIO(_DATA) as f:
    plurals: list[tuple[str, str, int]] = [
        (row[0], row[1], get_valency(row[3])) for row in csv.reader(f, delimiter="\t")
    ]
