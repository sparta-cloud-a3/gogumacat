from flask import Flask, render_template, jsonify, request, redirect, url_for, session, copy_current_request_context
from pymongo import MongoClient
from threading import Lock
# from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect

import jwt
import hashlib
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

import math
from json import dumps

async_mode = None

app = Flask(__name__)
# socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

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

#회원 로그인
@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)

#카카오 로그인
@app.route('/kakao_sign_in', methods=['POST'])
def kakao_sign_in():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    nickname_receive = request.form['nickname_give']
    img_receive = request.form['img_give']

    pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token, 'msg' : '카카오 로그인 성공\n초기 비밀번호...변경하셨죠..?ㅠㅠㅠ'})
    # 카카오로 로그인이 처음이라면 DB에 저장해서 회원가입을 먼저 시킨다.
    else:
        doc = {
            "username": username_receive,
            "password": pw_hash,
            "profile_name": username_receive,
            "profile_pic": img_receive,
            "profile_pic_real": "profile_pics/profile_placeholder.png",
            "profile_info": "",
            "nickname": nickname_receive,
            "address": ''
        }
        db.users.insert_one(doc)

        #DB 업데이트 이후 토큰 발행

        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token, 'msg' : f'아이디와 초기 비밀번호는 "{username_receive}"입니다!\n개인정보를 위해 반드시 변경해주세요!'})


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
        "username": username_receive,  # 아이디
        "password": password_hash,  # 비밀번호
        # "profile_name": username_receive,                           # 프로필 이름 기본값은 아이디 -> 이부분이 닉네임이 이니깐 없어도 될듯
        "profile_pic": "",  # 프로필 사진 파일 이름
        "profile_pic_real": "profile_pics/profile_placeholder.png",  # 프로필 사진 기본 이미지
        "profile_info": "",  # 프로필 한 마디
        "nickname": nickname_receive,  # 닉네임
        "address": address_receive
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
        address_receive = request.form["address_give"]
        password_receive = request.form["password_give"]
        pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
        new_doc = {
            "nickname": name_receive,
            "profile_info": about_receive,
            "address": address_receive,
            "password": pw_hash
        }
        if 'file_give' in request.files:
            file = request.files["file_give"]
            filename = secure_filename(file.filename)
            extension = filename.split(".")[-1]
            file_path = f"profile_pics/{username}.{extension}"
            file.save("./static/" + file_path)
            new_doc["profile_pic"] = filename
            new_doc["profile_pic_real"] = file_path
        db.users.update_one({'username': payload['id']}, {'$set': new_doc})
        return jsonify({"result": "success", 'msg': '프로필을 업데이트했습니다.'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route('/listing', methods=['GET'])
def listing_page():
    order = request.args.get('order')
    # default는 1이고 type은 int
    page = request.args.get('page', 1, type=int)
    # 한 페이지당 9개 보여줌
    limit = 9

    posts = list(db.posts.find({}, {'_id': False}))
    total_count = len(posts)
    last_page_num = math.ceil(total_count / limit)

    if order == 'like':
        for i in range(total_count):
            db.posts.update_one({'idx':posts[i]['idx']}, {'$set': {'like_count': db.likes.count_documents({"idx": posts[i]['idx']})}})
        posts = list(db.posts.find({}, {'_id': False}).sort('like_count', -1).skip((page - 1) * limit).limit(limit))
    else:
        posts = list(db.posts.find({}, {'_id': False}).sort('_id', -1).skip((page - 1) * limit).limit(limit))
        for i in range(len(posts)):
            posts[i]['like_count'] = db.likes.count_documents({"idx": posts[i]['idx']})

    return jsonify({'posts': posts, 'limit': limit, 'page': page, 'last_page_num': last_page_num})


@app.route('/search', methods=['GET'])
def searching_page():
    query_receive = request.args.get('query')
    order = request.args.get('order')
    # default는 1이고 type은 int
    page = request.args.get('page', 1, type=int)
    # 한 페이지당 9개 보여줌
    limit = 9

    posts = list(db.posts.find({'$or': [{'title': {'$regex': query_receive}}, {'content': {'$regex': query_receive}}]},
                      {'_id': False}))
    total_count = len(posts)
    last_page_num = math.ceil(total_count / limit)

    if order == 'like':
        for i in range(total_count):
            db.posts.update_one({'idx': posts[i]['idx']}, {'$set': {'like_count': db.likes.count_documents({"idx": posts[i]['idx']})}})
        posts = list(
            db.posts.find({'$or': [{'title': {'$regex': query_receive}}, {'content': {'$regex': query_receive}}]},
                          {'_id': False}).sort('like_count', -1).skip((page - 1) * limit).limit(limit))
    else:
        posts = list(
            db.posts.find({'$or': [{'title': {'$regex': query_receive}}, {'content': {'$regex': query_receive}}]},
                          {'_id': False}).sort('_id', -1).skip((page - 1) * limit).limit(limit))
        for i in range(len(posts)):
            posts[i]['like_count'] = db.likes.count_documents({"idx": posts[i]['idx']})

    return jsonify(
        {"query": query_receive, "posts": posts, 'limit': limit, 'page': page, 'last_page_num': last_page_num})


@app.route("/get_posts", methods=['GET'])
def get_my_posts():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        username_receive = request.args.get("username_give")
        if username_receive == "":
            posts = list(db.posts.find({}, {'_id': False}).sort('date', -1))
        else:
            posts = list(db.posts.find({"username": username_receive}, {'_id': False}).sort("date", -1))
            comments = list(db.comments.find({"username": username_receive}, {'_id': False}).sort('_id', -1))
            reviews = ""
            likes = list(db.likes.find({"username": username_receive}, {'_id': False}).sort('_id', -1))

            for i in range(len(comments)):
                comments[i] = db.posts.find_one({'idx': comments[i]['idx']}, {'_id': False})
            for i in range(len(likes)):
                likes[i] = db.posts.find_one({'idx': likes[i]['idx']}, {'_id': False})

        return jsonify({'posts': posts, 'comments': comments, 'reviews': reviews, 'likes': likes})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


# 유저 개인의 물품 등록페이지 띄우기
@app.route('/posting/<username>')
def post_page(username):
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    username = payload["id"]
    user_info = db.users.find_one({"username": username}, {"_id": False})

    return render_template("posting.html", user_info=user_info)


# 등록할 내용 DB저장
@app.route('/user_post', methods=['POST'])
def posting():
    print(request.form)
    # DB 포스트 값에 고유번호 부여하기
    if 0 >= db.posts.estimated_document_count():
        idx = 1
    else:
        idx = list(db.posts.find({}, sort=[('_id', -1)]).limit(1))[0]['idx'] + 1
    # 토큰확인
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        userdata = db.users.find_one({"username": payload["id"]})  # payload속 id 값 받기
        # 클라이언트 post 데이터 받기
        username = userdata['username']
        nickname = userdata['nickname']
        print(username, nickname)
        title = request.form['title_give']
        date = request.form['date_give']
        price = request.form['price_give']
        file = request.files['file_give']
        content = request.form['content_give']
        address = request.form['address_give']
        print(title, date, price, file, content, address)

        # 현재 시각 체크하기
        today = datetime.now()
        mytime = today.strftime('%Y-%m-%d-%H-%M-%S')

        # 파일 확장자 빼고 시간을 이름에 붙이기
        extension = file.filename.split('.')[-1]
        filename = f'file-{mytime}'
        print(extension, filename)
        # static폴더에 파일 저장
        save_to = f'static/post_pic/{filename}.{extension}'
        file.save(save_to)
        # 데이터 DB에 저장하기
        doc = {
            'idx': idx,
            'username': username,
            'nickname': nickname,
            'title': title,
            'date': date,
            'price': price,
            'file': f'{filename}.{extension}',
            'content': content,
            'address': address,
        }
        print(doc)
        db.posts.insert_one(doc)
        return jsonify({"result": "success", 'msg': '등록이 완료되었습니다.'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect()

@app.route('/posts/<int:idx>')
def detail(idx):
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    username = payload["id"]
    user_info = db.users.find_one({"username": username}, {"_id": False})
    post = db.posts.find_one({'idx': int(idx)}, {'_id': False})

    post["like_count"] = db.likes.count_documents({"idx": int(idx)})
    post["like_by_me"] = bool(db.likes.find_one({"idx": int(idx), "username": payload['id']}))

    return render_template("post.html", post = post, user_info=user_info)

@app.route('/update_like', methods=['POST'])
def update_like():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        idx_receive = request.form["idx_give"]
        action_receive = request.form["action_give"]
        doc = {
            "idx": int(idx_receive),
            "username": user_info["username"]
        }
        if action_receive == "like":
            db.likes.insert_one(doc)
        else:
            db.likes.delete_one(doc)
        count = db.likes.count_documents({"idx": int(idx_receive)})

        return jsonify({"result": "success", "count": count})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

@app.route('/check', methods=['POST'])
def check_pw():
    password_receive = request.form['password_give']

    token_receive = request.cookies.get('mytoken')

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])

        pw_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
        result = bool(db.users.find_one({'username': payload["id"], 'password': pw_hash}))

        return jsonify({'result': result})

    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))



# def background_thread():
#     """Example of how to send server generated events to clients."""
#     count = 0
#     while True:
#         socketio.sleep(10)
#         count += 1
#         # socketio.emit('my_response',
#         #               {'data': 'Server generated event', 'count': count})
#
# @socketio.event
# def my_event(message):
#     session['receive_count'] = session.get('receive_count', 0) + 1
#     emit('my_response',
#          {'data': message['data'], 'count': session['receive_count'],'type':2})
#
#
# @socketio.event
# def join(message):
#     join_room(message['room'])
#     session['receive_count'] = session.get('receive_count', 0) + 1
#     emit('my_response',
#          {'data': '',
#           'count': session['receive_count'],'type': message['type']},
#          to=message['room'])
#
#
# @socketio.event
# def leave(message):
#     leave_room(message['room'])
#     session['receive_count'] = session.get('receive_count', 0) + 1
#     emit('my_response',
#          {'data': 'In rooms: ' + ', '.join(rooms()),
#           'count': session['receive_count']})
#
#
# @socketio.on('close_room')
# def on_close_room(message):
#     session['receive_count'] = session.get('receive_count', 0) + 1
#     emit('my_response', {'data': 'Room ' + message['room'] + ' is closing.',
#                          'count': session['receive_count']},
#          to=message['room'])
#     close_room(message['room'])
#
#
# @socketio.event
# def my_room_event(message):
#     session['receive_count'] = session.get('receive_count', 0) + 1
#     emit('my_response',
#          {'data': message['data'], 'count': session['receive_count'],'type':message['type']},
#          to=message['room'])
#
#
# @socketio.event
# def disconnect_request():
#     @copy_current_request_context
#     def can_disconnect():
#         disconnect()
#
#     session['receive_count'] = session.get('receive_count', 0) + 1
#     emit('my_response',
#          {'data': 'Disconnected!', 'count': session['receive_count']},
#          callback=can_disconnect)
#
#
# @socketio.event
# def connect():
#     global thread
#     with thread_lock:
#         if thread is None:
#             thread = socketio.start_background_task(background_thread)
#     emit('my_response', {'data': '연결되었습니다.', 'count': 0 , 'type': 2})
#
#
# @socketio.on('disconnect')
# def test_disconnect():
#     print('Client disconnected', request.sid)


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
