# Qwen 성경 상담 서버

저장소 루트에서 `python3 server/app.py`를 실행하고 http://127.0.0.1:8765/ 에 접속한다.
Python 3.9 이상과 Ollama의 `qwen3:14b`가 필요하다. 외부 Python 패키지는 필요 없다.
Ollama는 127.0.0.1:11434에서 실행하며 자체 포트를 인터넷에 공개하지 않는다.

## 공개 GitHub Pages 연결

현재 `counsel-config.js`는 임시 Cloudflare Tunnel의 `/api/chat`을 사용한다.
로컬 화면에서는 같은 출처의 `/api/chat`을 사용한다.
터널 명령:

```sh
cloudflared tunnel --url http://127.0.0.1:8765 --http-host-header 127.0.0.1:8765 --no-autoupdate
```

터널을 다시 시작하면 주소가 달라진다. 새 HTTPS 주소로 `counsel-config.js`를 수정하고
GitHub Pages에 다시 배포해야 한다. 고정 운영에는 도메인과 이름이 있는 터널이 필요하다.
컴퓨터·Ollama·상담 서버·터널이 켜져 있고 절전하지 않아야 응답한다.
현재 프로세스는 재부팅 시 자동으로 시작하지 않는다.

공개 브라우저 Origin은 `https://wonseong620.github.io`만 허용한다. 같은 출처의 다른 경로도
동일 Origin이다. CORS는 사용자 인증이 아니며 API는 공개 서비스다.
서버의 Host 확인을 위해 위의 `--http-host-header` 옵션을 유지한다.
Pages 배포는 화면·스크립트·성경 다운로드·QR 파일만 포함한다.
서버 소스·테스트·운영 횟수 DB는 Pages 배포 산출물에 포함하지 않는다.

## 일일 100회 응답

- 전체 이용자의 **정상적으로 생성 완료한 응답 합산 100회**. 사람 수나 요청 수가 아니다.
- 한국시간(Asia/Seoul) 응답 완료 날짜를 기준으로 계산하며 자정에 새 일자의 한도를 사용한다.
- 모델 실패·잘못된 요청·혼잡 거절은 차감하지 않는다.
- 생성 완료 후 통신이 끊기더라도 생성된 답변은 1회로 계산한다.
- 실패나 프로세스 종료는 SQLite 트랜잭션을 롤백한다. 성공 횟수는 재시작 후에도 유지한다.
- 기본 DB: `~/.local/share/bible-counsel/quota.sqlite3`. 날짜와 완료 횟수만 저장한다.
- `COUNSEL_QUOTA_DB`로 DB 경로를 바꿀 수 있다. 운영 중 DB를 삭제하거나 바꾸면 집계가 초기화되므로 유지해야 한다.
- 동시에 답변 하나만 생성한다. 100회 소진과 일시적인 혼잡은 서로 다른 오류 안내를 반환한다.
- 상태와 응답에 남은 횟수를 반환하며 화면에 표시한다. 실시간 푸시는 아니므로 다음 요청 시 갱신된다.

## API와 모델

- GET `/api/health`: Ollama 연결·모델 설치 상태와 quota. 생성 속도까지 보장하지 않는다.
- POST `/api/chat`: messages 배열 → reply, model, verses, quota.
- 메시지 역할, 길이, 총 요청 크기, Origin·Host를 검증한다.
- `COUNSEL_MODEL`로 모델, `COUNSEL_PORT`로 서버 포트를 변경한다.
- think:false, JSON 스키마 응답, 1,000 생성 토큰, 8,192 컨텍스트.
- Ollama 요청 제한 150초, 화면 제한 165초. 임시 터널에도 별도 네트워크 제한이 있을 수 있다.
- 상담 본문이나 요청 경로를 서버 로그·DB에 저장하지 않는다. Cloudflare와 Ollama의 운영 로그는 각각 별도로 관리된다.
- Qwen은 해석과 응답을 생성하고 인용문은 TSV에서 조립한다. 생성 해석의 정확성을 자동 보장하지 않는다.
- 직접 장절·주제 사전·키워드 검색 기준선이다. 의미 검색은 미구현이며 결과의 관련성은 별도 품질 평가가 필요하다.
- 같은 장의 앞뒤 3절을 전달한다. 장 경계에서는 문맥이 적을 수 있다.
- 최근 대화만 전달하므로 긴 대화의 이전 내용은 잊을 수 있다.

검증: `python3 -m unittest discover -s tests -v`

참고: https://docs.ollama.com/api/chat
https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/
