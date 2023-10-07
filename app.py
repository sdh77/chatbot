from flask import Flask, request, jsonify, render_template
#from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
#from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.pipeline import make_pipeline
from flask_sqlalchemy import SQLAlchemy
import re                               # 문자열에서 특정 패턴 찾기


############ 규칙 기반 챗봇 (장바구니 기능) ############
# 사용자의 입력에서  DB 안에 있는 메뉴 명인지, 수량은 몇개인지 분석
def shop_parse_UserInput(user_input):
    dbMenu_Name = [menu.name for menu in Menu.query.all()]
    for menu in dbMenu_Name:
        if menu in user_input:
            quantity_match = re.search(r'(\d+)개', user_input)
            if quantity_match:
                quantity = quantity_match.group(1)
            else:
                quantity = "1"
            return (menu, quantity)
    return (None, None)
# 대응 메시지 생성
def shop_parse_response(menu, quantity):
    if menu:
        return { 
            "message": f"{menu} {quantity}개 주문하시겠습니까?",
            "action": "chat-shoppingCart-popup",
            "menu": menu,
            "quantity": quantity
        }
    else:
        return "해당 메뉴를 찾을 수 없습니다."              # 비슷한 메뉴명이 있으면 추천 기능도



############ 추천형 챗봇 (머신러닝 모델) ############
# 학습 데이터, 별도 파일로 분류하기. 
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

model = make_pipeline(TfidfVectorizer(), SVC()).fit(X_train, y_train)
# 취향대로 추천해 줘 -> 머신러닝 모델 사용
def machine_recommendation(user_message):
    response = model.predict([user_message])
    return response[0]


############ 트리형 챗봇 ############
# 사용자와의 대화를 추적하는 전역 변수 (장바구니,주문,챗봇 추적 / 챗봇 세부 추적)
parent_state = "initial"
child_state = "initial"

# 트리형 로직
def tree_logic(user_message):
    global parent_state, child_state, menu, quantity

    if parent_state == "initial":
        if child_state == "initial":
            menu, quantity = shop_parse_UserInput(user_message)     # 장바구니 기능을 위한 변수
            if menu and quantity:
                parent_state = "shop"
                child_state = "shop-checkout"
                return shop_parse_response(menu, quantity)
            elif "주문" in user_message:
                parent_state = "order"
                return
            elif "키오스키야" in user_message:          # users/index.html 에서 "키오스키야" 처리해야 함
                parent_state = "chatbot"
                child_state = "chatbot-initial"
                return
            else:
                return "죄송합니다. 이해하지 못했어요."

    elif parent_state == "shop":
        if child_state == "shop-checkout":
            if "개" in user_message:                 # "아냐 2개 주문할래"
                quantity_match = re.search(r'(\d+)개', user_message)
                if quantity_match:
                    quantity = quantity_match.group(1)
                    return f"{menu} {quantity}개 주문하시겠습니까?"
            elif "응" in user_message or "어" in user_message or "맞아" in user_message or "네" in user_message:
                parent_state = "initial"
                child_state = "initial"
                return "장바구니에 담았습니다."
            elif "취소" in user_message or "잘못" in user_message or "전으로" in user_message:  # 아냐는 수량조절과 취소할 때 중복... 
                parent_state = "initial"
                child_state = "initial"
                return "장바구니를 취소했습니다."


    elif parent_state == "chatbot":
        if child_state == "chatbot-initial":
            if "메뉴 검색" in user_message:
                child_state = "searchMenu"
                return "검색할 메뉴나 재료를 말씀해주세요..."
            elif "추천 메뉴" in user_message:
                child_state = "recommendMenu"
                return "사장님 추천 메뉴를 보여드릴게요..."
            elif "나에게 맞는 추천" in user_message:
                child_state = "personalMenu"
                return "알맞는 메뉴 추천을 위해 정보를 알려주세요. 잘 먹거나 못 먹는 음식, 맵기 등 자유롭게 말씀해주세요..."
            elif "직원 호출" in user_message:
                child_state = "service"
                return "직원을 호출합니다..."
        # elif child_state == "searchMenu":
    else:
        parent_state = "default"
        return "이해하지 못했습니다. 다시 한 번 말씀해주세요."
    





# Flask 앱 생성
app = Flask(__name__)


# AJAX를 사용한 챗봇
@app.route("/chat", methods=["POST"])
def chat_test():
    user_message = request.json["message"]
   
    # 먼저 트리형 로직 체크
    tree_response = tree_logic(user_message)

    if isinstance(tree_response, dict):
        return jsonify(tree_response)

    elif tree_response:
        return jsonify({"response": tree_response})

    # 사용자가 "취향대로 추천해 줘" 라고 한 경우만 머신러닝 로직 체크
    elif parent_state == "chatbot":
      return jsonify({"response": machine_recommendation(user_message)})

    # 그 외의 경우
    return jsonify({"response": "이해하지 못했습니다."})



##############chef

# def chef_Tree(chef_message):
#     if "번" in chef_message and "완료" in chef_message and "번테이블" in chef_message:
#         matchTable = re.search(r'(\d+)번테이블', chef_message)
#         matchMenu = re.search(r'(\d+)번', chef_message)
        
#     if "완료" in chef_message and "테이블" in chef_message:
#         quantity_match = re.search(r'(\d+)테이블', chef_message)
        
#         dbMenu_Name = [menu.name for menu in Menu.query.all()]
#         for menu in dbMenu_Name:
#             if menu in chef_message:
#                 quantity_match = re.search(r'(\d+)번', chef_message)
#                 if quantity_match:
#                     quantity = quantity_match.group(1)
#                 else:
#                     quantity = "1"
#                 return (menu, quantity)





# @app.route("/chat", methods=["POST"])
# def chat_test():
# return render_template("chat.html")

@app.route("/chef", methods=["POST"])
def chef_chat():
    # return render_template("chat.html")
    chef_message = request.json["message"]
    if "번 완료" in chef_message and "번 테이블" in chef_message :
        
        matchMenu = re.search(r'(\d+)번 완료', chef_message)
        
        if matchMenu:
            num = matchMenu.group(1)
        else:
            num = -1
        matchTable = re.search(r'(\d+)번 테이블', chef_message)
        table = matchTable.group(1)
        
        # if matchTable:
        #     table = matchTable.group(1)
        # else:
        #     matchTable = -1
        return { 
            "action": "completeMenu",
            "table": table,
            "matchMenu": num,
        }
    elif "번 테이블" in chef_message and "완료" in chef_message :
        matchTable = re.search(r'(\d+)번 테이블', chef_message)
        if matchTable:
            table = matchTable.group(1)
        else:
            matchTable = -1
        
        return {
            "action": "completeTable",
            "table": table,     
        }
    # 먼저 트리형 로직 체크
    # chef_Tree = tree_logic(chef_message)

    # if isinstance(chef_Tree, dict):
    #     return jsonify(tree_response)

    # elif tree_response:
    #     return jsonify({"response": tree_response})

    # # 사용자가 "취향대로 추천해 줘" 라고 한 경우만 머신러닝 로직 체크
    # elif parent_state == "chatbot":
    #   return jsonify({"response": machine_recommendation(user_message)})

    # # 그 외의 경우
    # return jsonify({"response": "이해하지 못했습니다."})



### 데이터베이스 연동 ###
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

@app.route("/")
def chat_page():
    return render_template("chat.html")