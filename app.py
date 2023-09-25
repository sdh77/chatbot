# import
from flask import Flask, request, jsonify, render_template
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from flask_sqlalchemy import SQLAlchemy

### 추천형 챗봇 (머신러닝 모델) ###
# 학습 데이터
training_data = [
    ("안녕", "안녕하세요!"),
    ("메뉴 추천해줘", "부채살 스테이크, 우삼겹 마라 오일 스파게티가 인기메뉴입니다."),
    ("다이어트에 좋은 음식을 알려줘", "샐러드 종류를 곁들여 드세요."),
    ("매운 음식을 보여줘", "스파이시 투움바는 어떠세요?"),
    ("영업 시간이 언제야?", "오전 9시부터 오후 10시까지입니다.")
]
# 모델 훈련
X_train = [x[0] for x in training_data]
y_train = [x[1] for x in training_data]

model = make_pipeline(CountVectorizer(), LogisticRegression()).fit(X_train, y_train)


### 트리형 챗봇 ###
# 사용자와의 대화를 추적하는 전역 변수
current_state = "initial"

# 트리형 로직
def tree_logic(user_message):
    global current_state

    if current_state == "initial":
        if "메뉴 검색해 줘" in user_message:
            # current_state = "menu_db"
            current_state = "initial"
            return "원하시는 메뉴 이름이나 재료를 말씀해주세요.."
        elif "추천 메뉴 알려 줘" in user_message:
            # current_state = "menu_db"
            current_state = "initial"
            recommended_menus = Menu.query.filter_by(recommend=True).all()
            if recommended_menus:
                menu_names = [menu.name for menu in recommended_menus]
                response_msg = "사장님 추천 메뉴를 보여드릴게요.. " + ", ".join(menu_names)
            else:
                response_msg = "현재 추천하는 메뉴가 없습니다."
            return response_msg
        elif "취향대로 추천해 줘" in user_message:
            current_state = "user_recommend"
            return "키오스키가 입맛에 맞게 추천해드릴게요. 저만 믿으세요!"
        elif "주문 도와줘" in user_message:
            current_state = "order"
            return "주문을 도와드릴게요. (장바구니 확인 / 결제)!"
        elif "직원 호출해 줘" in user_message:
            current_state = "service"
            return "어떤 서비스를 도와드릴까요?"
        else:
            current_state = "default"
            return "이해하지 못했습니다."
    # elif current_state == "menu_db":

    return None


# 취향대로 추천해 줘 -> 머신러닝 모델 사용
def machine_recommendation(user_message):
    response = model.predict([user_message])
    return response[0]


# Flask 앱 생성
app = Flask(__name__)


# 데이터베이스 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://hanium_kioski:aaa@localhost/ilprimo'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
db = SQLAlchemy(app)
# 데이터베이스 테이블 모델 정의
class Menu(db.Model):
    __tablename__ ='menu'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    price = db.Column(db.Integer)
    div = db.Column(db.String(20))
    recommend = db.Column(db.Boolean)
    spicy = db.Column(db.Integer)
    cnt = db.Column(db.Integer)
    new = db.Column(db.Boolean)
    index = db.Column(db.Integer)
    trash = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<menu {self.name}>'
# 데이터베이스 연동
@app.route('/dbmenu')
def get_dbmenu():
    try:
        dbmenu = Menu.query.all()
        if dbmenu:
            app.logger.info("Successfully fetched data from the database.")
        else:
            app.logger.warning("No data found in the database.")
        return render_template('menus.html', menus=dbmenu)
    except Exception as e:
        app.logger.error(f"Database error: {e}")
        return str(e), 500


# AJAX를 사용한 챗봇
@app.route("/chat", methods=["POST"])
def chat_test():
    user_message = request.json["message"]
   
    # 먼저 트리형 로직 체크
    tree_response = tree_logic(user_message)
    if tree_response:
        return jsonify({"response": tree_response})

    # 사용자가 "취향대로 추천해 줘" 라고 한 경우만 머신러닝 로직 체크
    elif current_state == "user_recommend":
      return jsonify({"response": machine_recommendation(user_message)})

    # 그 외의 경우
    return jsonify({"response": "이해하지 못했습니다."})

@app.route("/")
def chat_page():
    return render_template("chat.html")
