"""Fixed-vocabulary aggregates only; never persist arbitrary extracted words."""
TOPICS = {
 '마음과 감정': ('불안','걱정','염려','두려','슬프','슬퍼','우울','외로','외롭','지쳐','지친','스트레스'),
 '관계와 소통': ('관계','친구','갈등','다툼','대화','소통','용서','배신'),
 '일과 진로': ('직장','취업','면접','진로','직업','이직','퇴사','사업','업무'),
 '가족과 결혼': ('가족','부모','아버지','어머니','자녀','남편','아내','결혼','부부','육아'),
 '신앙과 기도': ('신앙','기도','믿음','교회','하나님','예배','성경'),
 '생활과 경제': ('경제','생활비','빚','대출','월세','소득','저축'),
 '건강과 돌봄': ('건강','아프','아파','질병','병원','간병','돌봄','수면','잠을'),
 '학업과 성장': ('학업','공부','시험','성적','학교','진학','성장'),
 '상실과 회복': ('상실','이별','돌아가','사별','장례','회복'),
}
KEYWORDS = {
 '불안': ('불안','걱정','염려'), '두려움': ('두려','무서'), '외로움': ('외로','외롭'),
 '관계': ('관계',), '소통': ('소통','대화'), '갈등': ('갈등','다툼'), '용서': ('용서',),
 '취업': ('취업','면접'), '진로': ('진로','직업'), '직장': ('직장','업무','이직','퇴사'),
 '가족': ('가족','부모','아버지','어머니','자녀'), '결혼': ('결혼','남편','아내','부부'),
 '육아': ('육아',), '신앙': ('신앙','믿음'), '기도': ('기도',), '교회': ('교회','예배'),
 '경제': ('경제','생활비','빚','대출','월세'), '건강': ('건강','질병','병원','아프','아파'),
 '돌봄': ('돌봄','간병'), '수면': ('수면','잠을','불면'), '학업': ('학업','공부','시험','성적'),
 '자존감': ('자존감','자신감','쓸모없'), '피로': ('피로','피곤','지쳐','지친','번아웃'),
 '상실': ('상실','사별','돌아가','장례'), '이별': ('이별',), '회복': ('회복',),
 '감사': ('감사',), '희망': ('희망','소망'),
}
MIN_COUNT = 5


def classify(text):
    # Each label can contribute at most once per successful initial exchange.
    return {'topic':[label for label,words in TOPICS.items() if any(w in text for w in words)][:3],
            'keyword':[label for label,words in KEYWORDS.items() if any(w in text for w in words)][:7]}


def initialize(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS daily_trends (day TEXT NOT NULL, kind TEXT NOT NULL, label TEXT NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(day,kind,label))')


def record(conn,day,labels):
    for kind,vocabulary in (('topic',TOPICS),('keyword',KEYWORDS)):
        for label in set(labels.get(kind,[])):
            if label not in vocabulary: continue
            conn.execute('INSERT INTO daily_trends VALUES (?,?,?,1) ON CONFLICT(day,kind,label) DO UPDATE SET count=count+1',(day,kind,label))


def read(conn,day):
    result={'date':day,'minimum':MIN_COUNT,'topics':[],'keywords':[]}
    for kind,key in (('topic','topics'),('keyword','keywords')):
        rows=conn.execute('SELECT label FROM daily_trends WHERE day=? AND kind=? AND count>=? ORDER BY count DESC, label ASC LIMIT 10',(day,kind,MIN_COUNT))
        result[key]=[r[0] for r in rows]
    return result
