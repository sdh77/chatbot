from flask import Flask, render_template, request, jsonify
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

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

# Flask 앱 생성
app = Flask(__name__)

@app.route("/chat2", methods=["POST"])
def chat_test():
    user_message = request.json["message"]
    response = model.predict([user_message])
    return jsonify({"response": response[0]})

@app.route("/")
def chat_page():
    return render_template("chat.html")
