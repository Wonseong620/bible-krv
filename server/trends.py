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
# Public labels describe concerns, never diagnoses or arbitrary extracted names.
KEYWORDS = {
 '불안심리': ('불안','걱정','염려','두려','무서','조급','막막','최악의 상황'),
 '외로움': ('외로','외롭','혼자인','혼자라는','마음을 터놓을 사람이'),
 '대인관계': ('관계','친구','사람을 믿','눈치','거절'),
 '소통문제': ('소통','대화가 안','대화가 잘 안','말이 안 통','말이 통하지','말을 안 들어','말을 안들어','말을 듣지','말을 안 해','말을 안해','말을 못 하','말을 못하','마음을 전하','오해'),
 '관계갈등': ('갈등','다툼','다투','싸우','싸워','서운','배신'),
 '용서고민': ('용서','미워','원망'),
 '취업부담': ('취업','면접','구직','입사지원','입사 지원'),
 '진로고민': ('진로','직업','무슨 일을','어떤 일을 해야','맞는 길'),
 '직장생활': ('직장','업무','이직','퇴사','상사','출근'),
 '가족관계': ('가족','부모','아버지','어머니','엄마','아빠','자녀','아들','딸이','딸과'),
 '부부관계': ('결혼','남편','아내','부부','배우자'),
 '육아부담': ('육아','양육','아이를 키우','아이 키우'),
 '신앙고민': ('신앙','믿음','하나님이 멀','하나님을 믿'),
 '기도생활': ('기도',), '교회관계': ('교회','예배'),
 '경제부담': ('경제','생활비','빚','대출','월세','돈 걱정','돈이 부족'),
 '건강염려': ('건강','질병','병원','아프','아파'),
 '돌봄부담': ('돌봄','간병','돌보다','돌보느라'),
 '수면문제': ('수면','잠을','불면','잠이 안','잠들기 어려'),
 '학업부담': ('학업','공부','시험','성적'),
 '자존감고민': ('자존감','자신감','쓸모없','못난','제가 싫','제 자신이 싫','저를 받아들이'),
 '비교심리': ('비교','뒤처','뒤쳐','남들만','다들 성공'),
 '완벽주의': ('완벽','실수하면 안','실수해서는 안'),
 '마음소진': ('피로','피곤','지쳐','지친','번아웃','의욕이 없','쉬어도'),
 '상실슬픔': ('상실','사별','돌아가','장례','떠나보냈'),
 '이별아픔': ('이별','헤어졌','헤어진'), '회복희망': ('회복','다시 시작','희망','소망'),
 '감사생활': ('감사',), '감정조절': ('화가 나','화를 내','화를 참','분노','짜증'),
 '삶의방향': ('삶의 의미','살아가는 이유','목표를','선택을 앞두'),
}
MIN_COUNT = 1


def classify(text):
    # Phrase-level clues infer concern labels without storing or exposing free text.
    labels = [label for label,words in KEYWORDS.items() if any(w in text for w in words)]
    if any(label in labels for label in ('가족관계','부부관계')):
        labels = [label for label in labels if label != '대인관계']
    return {'topic':[label for label,words in TOPICS.items() if any(w in text for w in words)][:3],
            'keyword':labels[:7]}


def initialize(conn):
    conn.execute('PRAGMA secure_delete=ON')
    conn.execute('DROP TABLE IF EXISTS daily_trends')
    conn.execute('CREATE TABLE IF NOT EXISTS recent_exchanges (id INTEGER PRIMARY KEY AUTOINCREMENT, completed_at TEXT NOT NULL, question TEXT NOT NULL, reply TEXT NOT NULL)')
    conn.execute('DELETE FROM recent_exchanges WHERE id NOT IN (SELECT id FROM recent_exchanges ORDER BY id DESC LIMIT 100)')


def record(conn, completed_at, question, reply):
    conn.execute('INSERT INTO recent_exchanges(completed_at,question,reply) VALUES (?,?,?)', (completed_at,question,reply))
    conn.execute('DELETE FROM recent_exchanges WHERE id NOT IN (SELECT id FROM recent_exchanges ORDER BY id DESC LIMIT 100)')


def read(conn, day):
    # Derive fixed-vocabulary counts in memory. Never persist labels or expose text.
    counts = {'topic':{}, 'keyword':{}}
    for (question,) in conn.execute('SELECT question FROM recent_exchanges ORDER BY id DESC LIMIT 100'):
        for kind, labels in classify(question).items():
            for label in labels:
                counts[kind][label] = counts[kind].get(label, 0) + 1
    result = {'date':day, 'minimum':MIN_COUNT, 'window':100, 'topics':[], 'keywords':[]}
    for kind,key in (('topic','topics'),('keyword','keywords')):
        result[key] = [label for label,count in sorted(counts[kind].items(),key=lambda item:(-item[1],item[0])) if count >= MIN_COUNT][:10]
    return result
