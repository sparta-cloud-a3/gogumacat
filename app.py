from flask import Flask, render_template, jsonify, request, redirect, url_for
from pymongo import MongoClient

import jwt
import hashlib
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.gogumacat

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

SECRET_KEY = 'MSG'

@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        return render_template('index.html', user_info=user_info)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))


@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)


@app.route('/user/<username>')
def user(username):
    # 각 사용자의 프로필과 글을 모아볼 수 있는 공간
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        status = (username == payload["id"])  # 내 프로필이면 True, 다른 사람 프로필 페이지면 False

        user_info = db.users.find_one({"username": username}, {"_id": False})

        return render_template('user.html', user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/sign_in', methods=['POST'])
def sign_in():
    # 로그인
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
         'id': username_receive,
         'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)  # 로그인 24시간 유지
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


@app.route('/sign_up/save', methods=['POST'])
def sign_up():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    nickname_receive = request.form['nickname_give']
    address_receive = request.form['address_give']
    password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    doc = {
        "username": username_receive,                               # 아이디
        "password": password_hash,                                  # 비밀번호
        # "profile_name": username_receive,                           # 프로필 이름 기본값은 아이디 -> 이부분이 닉네임이 이니깐 없어도 될듯
        "profile_pic": "",                                          # 프로필 사진 파일 이름
        "profile_pic_real": "profile_pics/profile_placeholder.png", # 프로필 사진 기본 이미지
        "profile_info": "",                                         # 프로필 한 마디
        "nickname": nickname_receive,                               # 닉네임
        "address" : address_receive
    }
    db.users.insert_one(doc)
    return jsonify({'result': 'success'})


@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})


@app.route('/sign_up/check_dup_nick', methods=['POST'])
def check_dup_nick():
    nickname_receive = request.form['nickname_give']
    exists = bool(db.users.find_one({"nickname": nickname_receive}))
    return jsonify({'result': 'success', 'exists': exists})


@app.route('/update_profile', methods=['POST'])
def update_profile():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        username = payload["id"]
        name_receive = request.form["name_give"]
        about_receive = request.form["about_give"]
        new_doc = {
            "nickname": name_receive,
            "profile_info": about_receive
        }
        if 'file_give' in request.files:
            file = request.files["file_give"]
            filename = secure_filename(file.filename)
            extension = filename.split(".")[-1]
            file_path = f"profile_pics/{username}.{extension}"
            file.save("./static/"+file_path)
            new_doc["profile_pic"] = filename
            new_doc["profile_pic_real"] = file_path
        db.users.update_one({'username': payload['id']}, {'$set':new_doc})
        return jsonify({"result": "success", 'msg': '프로필을 업데이트했습니다.'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route('/listing', methods=['GET'])
def listing():
    order = request.args.get('order')
    print(order)
    if order == "like":
        posts = list(db.posts.find({}, {'_id': False}).sort('liked', -1))
    else:
        posts = list(db.posts.find({}, {'_id': False}).sort('_id', -1))

    return jsonify({"posts":posts})

@app.route('/search', methods=['GET'])
def search_listing():
    query_receive = request.args.get('query')
    posts = list(db.posts.find( { '$or': [ {'title': {'$regex': query_receive}}, {'content': {'$regex': query_receive}} ] }, {'_id': False}))

    return jsonify({"query": query_receive, "posts": posts})


@app.route('/posts/<int:id>', methods=['GET'])
def give_post(id):
    post = db.posts.find_one({'post_id': id}, {'_id': False})

    return render_template('post.html', post=post)

@app.route("/get_posts", methods=['GET'])
def get_my_posts():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        username_receive = request.args.get("username_give")
        if username_receive=="":
            posts = list(db.posts.find({}, {'_id': False}).sort('date', -1))
        else:
            posts = list(db.posts.find({"username":username_receive},{'_id': False}).sort("date", -1).limit(9))
        return jsonify({"posts": posts})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)