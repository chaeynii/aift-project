## AIFT 
- 8팀

## 5주차 현재 작업내용 정리
1. 브랜치 전략
  - GIT-FLOW 전략
  
   (feature, develop, release, hotfix, master) : 5가지 브랜치 사용
   1. Main : 배포용( 그 누구도 삭제할 수 없고 유지됨)
   2. Hotfix : master배포 후 발생되는 문제점들을 모아 개선하는 브런치이면 개선이 완료되면 develop, release, master에 머지된다.
   3. Release : 개발 후 수정, 버그 테스트를 거치기 전까지를 뜻하고, 이를 통과하면 master로 머지한다
   4. Develop : 개발 브런치, feature의 기능들이 하나씩 더해지며, 관리 되고 배포하게 될 수준에 도달할 경우 release로 머지한다.
   5. Feature : 기능 단위 브런치
  
  기존의 git flow전략에서 3개의 브런치(main develop feature)만을 사용한 feature-branch사용
  
  -Feature-브랜치 전략
  
    1. Main branch : 배포 브랜치로, 직접적인 push 절대불가
    2. Develop branch : 개인들이 브랜치를 만들어서 브랜치로 merge시키고 합쳐서 release해야할 때 main으로 이동
    3. Feature branch : 한 기능을 만들 때마다 새 브랜치 만들것이고 이를 develop으로 merge시키고 삭제시킴


2. 로그인 정보 불러오기 수행 및 오류 수정



## 역할분담
이채연 - 데이터 수집, DB 연결, 오류 수정, PPT 제작

송예진 - 데이터 수집, 파일 결합, 키움 API 연동, PPT 제작, 발표

## 협업내용
개인메세지를 통한 협의 & 이슈 글 작성하여 서로 협의
