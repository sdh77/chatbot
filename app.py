from flask import Flask, request, jsonify, render_template
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.pipeline import make_pipeline
from flask_sqlalchemy import SQLAlchemy
from fuzzywuzzy import process          # 유사 문자열 찾기
import re                               # 문자열에서 특정 패턴 찾기

import sys
# sys.path.append('/var/www/chatbot/data')    # 데이터 디렉토리 경로 삽입
# sys.path.append('/Users/yangsee/chatbot/data')    # 데이터 디렉토리 경로 삽입

# from koreanNum import korean_to_number, num_map
# from nlp_model import NLPHandler

############ 콜 리스트 ############
call_List = {
    "물", "물티슈", "숟가락", "젓가락", "앞치마", "앞접시", "휴지", "수저"
}
############ 페이지  리스트 ############
page_List = {
    "전체", "파스타", "라이스", "샐러드", "피자", "스테이크", "사이드", "음료", "와인 및 주류"
}
############ 숫자-한국어  리스트 ############
num_map = {
    '하나': 1, '한': 1, '둘': 2, '두': 2, '셋': 3, '세': 3, '넷': 4, '네': 4, '>다섯': 5, '여섯': 6, '일곱': 7, '여덟': 8, '아홉': 9, '열': 10
}


def korean_to_number(word):
    return num_map.get(word, None)


############ 키오스크: "어서오세요. 주문을 도와드리는 키오스키입니다." ############


############ 처음으로 ############
# 


############ 규칙 기반 챗봇 (장바구니 기능) ############
# 사용자의 입력에서, 메뉴 명을 잘못 입력했을 시, 유사한 메뉴를 추천하는 기능
def find_best_match(input_str, menuDB):
    best_match, score = process.extractOne(input_str, menuDB)
    if score > 80:
        return best_match
    return None
# 사용자의 입력에서  DB 안에 있는 메뉴 명인지, 수량은 몇개인지 분석


def shop_parse_UserInput(user_input):
    dbMenu_Name = [menu.name for menu in Menu.query.all()]
    quantity = "1"

    matched_menu = next(
        (menu for menu in dbMenu_Name if menu in user_input), None)

    if user_input in page_List:
        return None

    if user_input and not matched_menu and len(user_input) >= 2:
        matched_menu = find_best_match(user_input, dbMenu_Name)

    quantity_match = re.search(r'(\d+)개', user_input)
    if quantity_match:
        quantity = quantity_match.group(1)
    else:
        for word in num_map.keys():
            if word in user_input:
                quantity = str(korean_to_number(word))
                break

    return (matched_menu, quantity)

# 장바구니 팝업 생성 및 수정


def shop_parse_response(menu, quantity):
    if menu:
        return {
            "message": f"{menu} {quantity}개 장바구니에 담으시겠습니까?",
            "action": "chat-shoppingCart-popup",
            "menu": menu,
            "quantity": quantity
        }
    else:
        parent_state, child_state = "initial"
        return "해당 메뉴를 찾을 수 없습니다."  # 비슷한 메뉴 있으면 추천 기능


def shop_parse_responseEdit(menu, quantity):
    return {
        "message": f"{menu} {quantity}개 장바구니에 담으시겠습니까?",
        "action": "chat-shoppingCart-popup-Edit",
        "menu": menu,
        "quantity": quantity
    }


def shop_parse_responseOrderBtn():
    return {
        "message": f"장바구니에 담았습니다.",
        "action": "chat-shoppingCart-popup-orderBtn",
    }


def shop_parse_responseCloseBtn():
    return {
        "message": f"장바구니를 취소했습니다.",
        "action": "chat-shoppingCart-popup-closeBtn",
    }


############ 규칙 기반 챗봇 (주문 기능) ############
# 주문하기
def order_parse_response():
    return {
        "message": f"장바구니를 확인해주세요. 주문 내역이 맞으신가요?",
        "message2": f"장바구니가 비어있습니다.",
        "action": "orderBtn-popup-click-trigger"
    }


def order_parse_YesBtn():
    return {
        "message": f"주문이 완료되었습니다. 이용해 주셔서 감사합니다.",  # 몇분 기다리세요도 넣기
        "action": "orderBtn-click-trigger"
    }


def order_parse_NoBtn():
    return {
        "message": f"주문이 취소되었습니다.",  # 몇분 기다리세요도 넣기
        "action": "orderBtn-close-click-trigger"
    }


############ 규칙 기반 챗봇 (페이지 로드) ############
# 원하는 페이지 로드 (상단 메뉴바)
def pageLoad_parse_response(user_input):
    matchPage = re.search(r'([가-힣]+) (보여|주문).*', user_input)
    if matchPage:
        page = matchPage.group(1)
        if page in page_List:
            return {
                "message": f"{page} 페이지 입니다.",
                "action": "loadpage",
                "page": page
            }
    return {
        "message": f"{page} 페이지를 찾을 수 없습니다."
    }
# 원하는 페이지 로드 (uppage, downpage)


############ 규칙 기반 챗봇 (메뉴 검색 로드) ############
def pageLoad_parse_searchMenu(user_input):
    user_input_keyword = user_input
    matched_by_name = Menu.query.filter(
        Menu.name.like(f"%{user_input}%")).all()
    matched_by_ingredient = Menu.query.filter(
        Menu.ingredient.like(f"%{user_input}%")).all()
    all_matched = list(matched_by_name) + list(matched_by_ingredient)
    matched_menus = list(set(all_matched))
    menu_names = [menu.name for menu in matched_menus]
    menu_string = ','.join(menu_names)

    if menu_names:
        return {
            "message": f"{user_input_keyword} 검색 결과입니다.",
            "action": "loadpage-search",
            "searchMenus": menu_string
        }
    else:
        return {"message": f"{user_input_keyword} 메뉴가 없습니다."}


############ 규칙 기반 챗봇 (추천 메뉴 로드) ############
def pageLoad_parse_recommendMenu():
    recommend_menus = Menu.query.filter(Menu.recommend == True).all()
    menu_names = [menu.name for menu in recommend_menus]
    menu_string = ','.join(menu_names)

    return {
        "message": f"사장님 추천 메뉴를 보여드릴게요...",
        "action": "loadpage-recommend",
        "recommendMenus": menu_string
    }


############ 규칙 기반 챗봇 (매운거 로드) ############
# 주문하기
def spicy_parse_response():
    spicy_menus = Menu.query.filter(Menu.spicy > 0).all()
    menu_names = [menu.name for menu in spicy_menus]
    menu_string = ','.join(menu_names)
    return {
        "message": f"맵기 순으로 보여드릴게요... ",
        "action": "loadpage-spicy",
        "spicyMenus": menu_string
    }


############ 트리형 챗봇 ############
# 사용자와의 대화를 추적하는 전역 변수 (장바구니,주문,챗봇 추적 / 챗봇 세부 추적)
parent_state = "initial"
child_state = "initial"

# 트리형 로직


def tree_logic(user_message):
    global parent_state, child_state, menu, quantity

    if "처음으로" in user_message:
        parent_state = "initial"
        child_state = "initial"
        return "불편을 드려 죄송합니다. 다시 도와드릴게요" 

    if parent_state == "initial":
        if child_state == "initial":
            if "보여줘" in user_message or "보여 줘" in user_message:
                return pageLoad_parse_response(user_message)
            # 메뉴와 개수로 장바구니
            menu, quantity = shop_parse_UserInput(user_message)
            if menu and quantity:
                parent_state = "shop"
                child_state = "shop-checkout"
                return shop_parse_response(menu, quantity)
            elif "주문" in user_message:
                parent_state = "order"
                return order_parse_response()
            elif "매운" in user_message or "매콤한" in user_message or "스트레스" in user_message:
                return spicy_parse_response()
            elif "검색" in user_message or "찾아줘" in user_message or "찾고싶어" in user_message:
                parent_state = "search"
                return "검색할 키워드를 말씀해 주세요..."
            elif "추천" in user_message:
                return pageLoad_parse_recommendMenu()
            # 대화 스크립트 추가
            elif "안녕" in user_message or "여보세요" in user_message or "키 오 스 키 아" in user_message or "스퀘어" in user_message or "티오" in user_message or "새끼" in user_message or "스키" in user_message or "스 키" in user_message or "키 오" in user_message or "키즈 키야" in user_message:
                return "안녕하세요! 무엇을 도와드릴까요?"
            elif "뭐 먹을까" in user_message or "오늘 뭐 먹지" in user_message or "뭐 먹지" in user_message or "결정 장애" in user_message or "못 고르겠어" in user_message or "골라줘" in user_message or "못 고르겠다" in user_message or "빨리 골라" in user_message or "골라주라" in user_message:
                return pageLoad_parse_recommendMenu()
            elif "언제" in user_message or "영업" in user_message or "시간" in user_message or "언제까지 해" in user_message or "닫아" in user_message:
                return "오전 11시부터 오후 10시까지 입니다."
            elif "사용" in user_message:
                return "오늘 뭐 먹지 라고 말해보세요."
            elif "시끄" in user_message or "바보" in user_message or "멍청" in user_message or "멍충" in user_message:
                return "죄송합니다. 제가 도움이 되지 못한 것 같네요."
            elif "필요해" in user_message:
                matchCall = re.search(r'([가-힣]+) 필요해', user_message)
                if matchCall:
                    call = matchCall.group(1)
                    if (call not in call_List):
                        call = -1
                else:
                    call = -1
                return {
                    "message": f"{call}을 가져다드리겠습니다.",
                    "action": "call",
                    "matchCall": call,
                }
            elif "종업원 불러줘" in user_message or "직원 불러줘" in user_message:
                return {
                    "message": "잠시만 기다려주세요",
                    "action": "callEmployee",
                }
        else:
            return "이해 하지 못 했습니다. 다시 말씀해주세요."

    elif parent_state == "shop":
        if child_state == "shop-checkout":
            if "개" in user_message:                 # "아냐 2개 주문할래"
                quantity_match = re.search(r'(\d+)개', user_message)
                if quantity_match:
                    quantity = quantity_match.group(1)
                    return shop_parse_responseEdit(menu, quantity)
                else:
                    for word in num_map.keys():
                        if word in user_message:
                            quantity = str(korean_to_number(word))
                            return shop_parse_responseEdit(menu, quantity)
            # 아냐는 수량조절과 취소할 때 중복...
            elif "취소" in user_message or "아니" in user_message or "잘못" in user_message or "전으로" in user_message or "싫어" in user_message:
                parent_state = "initial"
                child_state = "initial"
                return shop_parse_responseCloseBtn()
            elif "응" in user_message or "웅" in user_message or "어" in user_message or "맞아" in user_message or "네" in user_message or "해줘" in user_message or "그래" in user_message or "좋아" in user_message or "해봐" in user_message or "오냐" in user_message or "알겠어" in user_message or "해주세요" in user_message or "알겠습니다" in user_message or "넵" in user_message or "넹" in user_message or "좋아요" in user_message or "그랭" in user_message or "할래" in user_message or "담아" in user_message or "넣어" in user_message or "추가" in user_message:
                parent_state = "initial"
                child_state = "initial"
                return shop_parse_responseOrderBtn()
            else:
                return "이해 하지 못 했습니다. 다시 말씀해주세요."

    elif parent_state == "order":
        if "취소" in user_message or "아니" in user_message or "잘못" in user_message or "전으로" in user_message or "싫어" in user_message:
            parent_state = "initial"
            return order_parse_NoBtn()
        elif "응" in user_message or "웅" in user_message or "어" in user_message or "맞아" in user_message or "네" in user_message or "해줘" in user_message or "그래" in user_message or "좋아" in user_message or "해봐" in user_message or "오냐" in user_message or "알겠어" in user_message or "해주세요" in user_message or "알겠습니다" in user_message or "넵" in user_message or "넹" in user_message or "좋아요" in user_message or "그랭" in user_message or "할래" in user_message:
            parent_state = "initial"
            return order_parse_YesBtn()
        else:
            return "이해 하지 못 했습니다. 다시 말씀해주세요."

    elif parent_state == "search":
        parent_state = "initial"
        return pageLoad_parse_searchMenu(user_message)

    else:
        return "이해 하지 못 했습니다. 다시 말씀해주세요."


############ Flask 앱 생성 #############
app = Flask(__name__)


# AJAX를 사용한 챗봇
############ 챗봇 연결 ############
@app.route("/chat", methods=["POST"])
def chat_test():
    user_message = request.json["message"]

    # 1. 먼저 트리형 로직 처리
    tree_response = tree_logic(user_message)

    if isinstance(tree_response, dict):
        return jsonify(tree_response)
    elif tree_response:
        return jsonify({"response": tree_response})

    # 2. NLP 응답
    # model_instance = NLPHandler()
    # intent = model_instance.classify_intent(user_message)
    # if intent == "recommend":
    #    return pageLoad_parse_recommendMenu()
    # elif intent == "greeting":
    #    return "안녕하세요"
    # elif intent == "farewell":
    #    return "안녕히 가세요"
    # elif intent == "test":
    #    return "hummmmmmm..."

    # 3. 알 수 없는 명령어 처리
    return jsonify({"response2": "다시 말씀해주세요."})


@app.route('/update_state', methods=['POST'])
############ AJAX를 통해 추적 상태 수정 ############
def update_state():
    global parent_state
    new_state = request.json.get('new_state')
    if new_state:
        parent_state = new_state
        return order_parse_response()
    return "연결 오류"


############ chef 주방장 메뉴 처리 상태 업데이트, 품절 관리 ############


def food_best_match(input_str):
    target_divs = ["파스타", "피자", "라이스", "샐러드", "스테이크", "사이드"]
    menuDB = [menu.name for menu in Menu.query.filter(
        Menu.div.in_(target_divs)).all()]

    best_match, score = process.extractOne(input_str, menuDB)
    if score > 70:
        return best_match
    return None


@app.route("/chef", methods=["POST"])
def chef_chat():
    # return render_template("chat.html")
    chef_message = request.json["message"]
    if "번 완료" in chef_message and "번 테이블" in chef_message:
        matchMenu = re.search(r'(\d+)번 완료', chef_message)

        if matchMenu:
            num = matchMenu.group(1)
        else:
            num = -1
        matchTable = re.search(r'(\d+)번 테이블', chef_message)
        # table = matchTable.group(1)

        if matchTable:
            table = matchTable.group(1)
        else:
            table = -1
        return {
            "action": "completeMenu",
            "table": table,
            "matchMenu": num,
        }
    elif "번 테이블" in chef_message and "완료" in chef_message:
        checkMenu = food_best_match(chef_message)
        if checkMenu:
            checkMenu = food_best_match(chef_message)
        else:
            checkMenu = "no menu"

        if checkMenu == "no menu":
            matchTable = re.search(r'(\d+)번 테이블', chef_message)
            if matchTable:
                table = matchTable.group(1)
            else:
                matchTable = -1

            return {
                "action": "completeTable",
                "table": table,
            }
        else:
            matchTable = re.search(r'(\d+)번 테이블', chef_message)

            if matchTable:
                table = matchTable.group(1)
            else:
                table = -1

            return {
                "action": "completeMenuName",
                "table": table,
                "matchMenu": checkMenu,
            }

    elif "품절 해제" in chef_message:
        soldOutMenu = food_best_match(chef_message)
        if soldOutMenu:
            soldOutMenu = food_best_match(chef_message)
        else:
            soldOutMenu = "no menu"

        return {
            "action": "noSoldOutMenu",
            "soldOutMenu": soldOutMenu,
        }

    elif "품절" in chef_message:
        soldOutMenu = food_best_match(chef_message)
        if soldOutMenu:
            soldOutMenu = food_best_match(chef_message)
        else:
            soldOutMenu = "no menu"
        return {
            "action": "soldOutMenu",
            "soldOutMenu": soldOutMenu,
        }


def drink_best_match(input_str):
    target_divs = ["음료", "와인", "주류"]
    menuDB = [menu.name for menu in Menu.query.filter(
        Menu.div.in_(target_divs)).all()]

    best_match, score = process.extractOne(input_str, menuDB)
    if score > 70:
        return best_match
    return None


def allMenu_best_match(input_str):
    menuDB = [menu.name for menu in Menu.query.all()]

    best_match, score = process.extractOne(input_str, menuDB)
    if score > 70:
        return best_match
    return None


@app.route("/employee", methods=["POST"])
def employee_chat():
    employee_message = request.json["message"]
    if "번 완료" in employee_message and "번 테이블" in employee_message:
        matchMenu = re.search(r'(\d+)번 완료', employee_message)

        if matchMenu:
            num = matchMenu.group(1)
        else:
            num = -1

        matchTable = re.search(r'(\d+)번 테이블', employee_message)

        if matchTable:
            table = matchTable.group(1)
        else:
            table = -1

        return {
            "action": "completeMenu",
            "table": table,
            "num": num
        }
    elif "번 테이블" in employee_message and "완료" in employee_message:

        matchTable = re.search(r'(\d+)번 테이블', employee_message)

        if matchTable:
            table = matchTable.group(1)
        else:
            table = -1

        checkMenu = allMenu_best_match(employee_message)
        if checkMenu:
            checkMenu = allMenu_best_match(employee_message)
        else:
            checkMenu = "no menu"

        if (checkMenu == "no menu"):
            if "호출" in employee_message:
                return {
                    "action": "completeCall",
                    "table": table
                }
            elif "음식" in employee_message:
                return {
                    "action": "completeFood",
                    "table": table
                }
            elif "주류" in employee_message:
                return {
                    "action": "completeDrink",
                    "table": table
                }
            
            else:
                return {
                    "action": "completeTable",
                    "table": table
                }
        else:
            return {
                "action": "completeMenuName",
                "table": table,
                "matchMenu": checkMenu
            }

    elif "품절 해제" in employee_message:
        soldOutMenu = drink_best_match(employee_message)
        if soldOutMenu:
            soldOutMenu = drink_best_match(employee_message)
        else:
            soldOutMenu = "no menu"
        return {
            "action": "noSoldOutMenu",
            "soldOutMenu": soldOutMenu,
        }

    elif "품절" in employee_message:
        soldOutMenu = drink_best_match(employee_message)
        if soldOutMenu:
            soldOutMenu = drink_best_match(employee_message)
        else:
            soldOutMenu = "no menu"
        return {
            "action": "soldOutMenu",
            "soldOutMenu": soldOutMenu,
        }


############ 데이터베이스 연동 ############
# 데이터베이스 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://hanium_kioski:aaa@localhost/ilprimo'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True

db = SQLAlchemy(app)
# 데이터베이스 테이블 모델 정의


class Menu(db.Model):
    __tablename__ = 'menu'
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
    ingredient = db.Column(db.String(50))

    def __repr__(self):
        return f'<menu {self.name}>'
# 데이터베이스 연동


@app.route('/dbmenu')
def get_dbmenu():
    try:
        # dbmenu = Menu.query.all()
        # target_divs = ["파스타", "피자", "라이스", "샐러드", "스테이크", "사이드"]
        # dbmenu = Menu.query.filter(Menu.div.in_(target_divs)).all()

        target_divs2 = ["음료", "와인", "주류"]
        dbmenu = Menu.query.filter(Menu.div.in_(target_divs2)).all()

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


@app.route("/chef")
def chef_page():
    return render_template("chef.html")


@app.route("/employee")
def employee_page():
    return render_template("employee.html")
