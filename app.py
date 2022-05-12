from flask import Flask, render_template, jsonify, request, redirect, url_for, session, copy_current_request_context
from pymongo import MongoClient
from threading import Lock
from flask_socketio import SocketIO, emit, join_room, leave_room, close_room, rooms, disconnect
import boto3
import os
import jwt
import hashlib
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import math
import requests


app = Flask(__name__)

async_mode = None
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock()

client = MongoClient('localhost', 27017)
db = client.gogumacat

app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['UPLOAD_FOLDER'] = "./static/profile_pics"

SECRET_KEY = 'MSG'  # [수정]배포 전 삭제해야됨


@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.users.find_one({"username": payload["id"]})
        return render_template('index.html', user_info=user_info, si_s=get_si())
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))

### 로그인 페이지 시작
# 로그인 페이지 이동
@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)


# 로그인
@app.route('/sign_in', methods=['POST'])
def sign_in():
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


# 카카오 로그인
@app.route('/kakao_sign_in', methods=['POST'])
def kakao_sign_in():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    nickname_receive = request.form['nickname_give']
    img_receive = request.form['img_give']
    password = password_receive.split('@')[0]


    pw_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    result = db.users.find_one({'username': username_receive, 'password': pw_hash})

    if result is not None:
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token, 'msg': '카카오 로그인 성공'})
    # 카카오로 로그인이 처음이라면 DB에 저장해서 회원가입을 먼저 시킨다.
    else:
        doc = {
            "username": username_receive,
            "password": pw_hash,
            "profile_pic": f'{img_receive}',
            "profile_pic_real": f'{img_receive}',
            "profile_info": "",
            "nickname": nickname_receive,
            "address": ''
        }

        db.users.insert_one(doc)

        # DB 업데이트 이후 토큰 발행
        payload = {
            'id': username_receive,
            'exp': datetime.utcnow() + timedelta(seconds=60 * 60 * 24)
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token, 'msg': f'카카오 회원가입 성공\n초기 비밀번호는 "{password}"입니다.\n비밀번호를 꼭 변경해주세요!'})


# 회원가입
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
        "profile_pic": "",  # 프로필 사진 파일 이름
        "profile_pic_real": "/static/profile_pics/profile_placeholder.png",  # 프로필 사진 기본 이미지
        "profile_info": "",  # 프로필 한 마디
        "nickname": nickname_receive,  # 닉네임
        "address": address_receive  # 주소
    }

    db.users.insert_one(doc)
    return jsonify({'result': 'success'})


# id 중복 확인
@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup_id():
    username_receive = request.form['username_give']
    exists = bool(db.users.find_one({"username": username_receive}))
    return jsonify({'result': 'success', 'exists': exists})


# 닉네임 중복 확인
@app.route('/sign_up/check_dup_nick', methods=['POST'])
def check_dup_nick():
    nickname_receive = request.form['nickname_give']
    exists = bool(db.users.find_one({"nickname": nickname_receive}))
    return jsonify({'result': 'success', 'exists': exists})

### 메인 페이지 시작
# 상품 목록 전체 조회
@app.route('/listing', methods=['GET'])
def listing_page():
    order = request.args.get('order') # 순서

    # pagination을 위해 필요한 정보
    page = request.args.get('page', 1, type=int)  # default는 1이고 type은 int
    limit = 9  # 한 페이지당 9개 보여줌
    posts = list(db.posts.find({}, {'_id': False}))
    total_count = len(posts)
    last_page_num = math.ceil(total_count / limit)

    if order == 'like': # 관심순 요청이면
        for i in range(total_count): # 관심 개수 update(관심순이기때문에 전체 게시물을 먼저 update)
            db.posts.update_one({'idx': posts[i]['idx']},
                                {'$set': {'like_count': db.likes.count_documents({"idx": posts[i]['idx']})}})

        # 요청한 페이지에 맞는 게시물을 limit만큼 전달
        posts = list(db.posts.find({}, {'_id': False}).sort('like_count', -1).skip((page - 1) * limit).limit(limit))
    else: # 최신순 요청이면
        # 요청한 페이지에 맞는 게시물을 limit만큼 전달
        posts = list(db.posts.find({}, {'_id': False}).sort('_id', -1).skip((page - 1) * limit).limit(limit))
        #관심 개수 update
        for i in range(len(posts)):
            posts[i]['like_count'] = db.likes.count_documents({"idx": posts[i]['idx']})

    return jsonify({'posts': posts, 'limit': limit, 'page': page, 'last_page_num': last_page_num})


# 검색 상품 목록 전체 조회
@app.route('/search', methods=['GET'])
def searching_page():
    query_receive = request.args.get('query') # 검색어

    order = request.args.get('order') # 순서

    # pagination을 위해 필요한 정보
    page = request.args.get('page', 1, type=int) # default는 1이고 type은 int
    limit = 9 # 한 페이지당 9개 보여줌
    posts = list(db.posts.find({'$or': [{'title': {'$regex': query_receive}}, {'content': {'$regex': query_receive}}]}, {'_id': False}))
    total_count = len(posts)
    last_page_num = math.ceil(total_count / limit)

    if order == 'like': # 관심순 요청이면
        for i in range(total_count): # 관심 개수 update(관심순이기때문에 전체 게시물을 먼저 update)
            db.posts.update_one({'idx': posts[i]['idx']},
                                {'$set': {'like_count': db.likes.count_documents({"idx": posts[i]['idx']})}})
        posts = list(
            db.posts.find({'$or': [{'title': {'$regex': query_receive}}, {'content': {'$regex': query_receive}}]},
                          {'_id': False}).sort('like_count', -1).skip((page - 1) * limit).limit(limit))
    else: # 최신순 요청이면
        posts = list(
            db.posts.find({'$or': [{'title': {'$regex': query_receive}}, {'content': {'$regex': query_receive}}]},
                          {'_id': False}).sort('_id', -1).skip((page - 1) * limit).limit(limit))
        for i in range(len(posts)): # 관심 개수 update
            posts[i]['like_count'] = db.likes.count_documents({"idx": posts[i]['idx']})

    return jsonify(
        {"query": query_receive, "posts": posts, 'limit': limit, 'page': page, 'last_page_num': last_page_num})


# 지역 데이터 리턴
def get_si():
    si = list(db.korea_address.distinct('si'))
    return si


# 입력받은 지역에 속한 동네 리턴
@app.route('/get_gu', methods=['GET'])
def get_gu():
    si = request.args.get('si') # 입력받은 지역
    if si == '세종특별자치시': # 세종시는 시군구 데이터가 없기 때문에 바로 읍면동 데이터로 넘어가게 함
        return jsonify({'gu': '세종특별자치시'})
    gu = list(db.korea_address.distinct('gu', {'si': si}))
    return jsonify({'gu': gu})


# 입력받은 동네에 속한 동 리턴
@app.route('/get_dong', methods=['GET'])
def get_dong():
    gu = request.args.get('gu') # 입력받은 동네
    if gu == '세종특별자치시': # 세종시는 시군구 데이터가 없기 때문에 지역데이터로 검색
        dong = list(db.korea_address.distinct('dong', {'si': gu}))
    else:
        dong = list(db.korea_address.distinct('dong', {'gu': gu}))
    return jsonify({'dong': dong})


# 입력받은 주소를 바탕으로 검색
@app.route('/search/address', methods=['GET'])
def search_by_address():
    si = request.args.get('si')
    gu = request.args.get('gu')
    dong = request.args.get('dong')

    order = request.args.get('order') # 순서

    #pagination에 필요한 정보
    page = request.args.get('page', 1, type=int) # default는 1이고 type은 int
    limit = 9 # 한 페이지당 9개 보여줌
    posts = list(db.posts.find({'address': {'$regex': dong}}, {'_id': False})) # 일단 동만 사용해서 검색
    total_count = len(posts)
    last_page_num = math.ceil(total_count / limit)

    if order == 'like': # 관심순 요청이면
        for i in range(total_count): # 관심 개수 update(관심순이기때문에 전체 게시물을 먼저 update)
            db.posts.update_one({'idx': posts[i]['idx']},
                                {'$set': {'like_count': db.likes.count_documents({"idx": posts[i]['idx']})}})
        posts = list(db.posts.find({'address': {'$regex': dong}}, {'_id': False}).sort('like_count', -1).skip(
            (page - 1) * limit).limit(limit))
    else: # 최신순 요청이면
        posts = list(
            db.posts.find({'address': {'$regex': dong}}, {'_id': False}).sort('_id', -1).skip((page - 1) * limit).limit(
                limit))
        for i in range(len(posts)): # 관심 개수 update
            posts[i]['like_count'] = db.likes.count_documents({"idx": posts[i]['idx']})
    return jsonify({"posts": posts, 'limit': limit, 'page': page, 'last_page_num': last_page_num})


# 현재 위치와 관련된 게시물 보여줌
@app.route('/search/myloc', methods=['GET'])
def search_by_location():
    # 일단 동만 사용해서 검색
    address = request.args.get("address")

    # pagination에 필요한 정보
    page = request.args.get('page', 1, type=int) # default는 1이고 type은 int
    limit = 9  # 한 페이지당 9개 보여줌
    total_count = db.posts.count_documents({})
    last_page_num = math.ceil(total_count / limit)
    posts = list(
        db.posts.find({'address': {'$regex': address}}, {'_id': False}).sort('_id', -1).skip((page - 1) * limit).limit(
            limit))

    for i in range(len(posts)): # 관심 개수 update
        posts[i]['like_count'] = db.likes.count_documents({"idx": posts[i]['idx']})

    return jsonify({"posts": posts, 'limit': limit, 'page': page, 'last_page_num': last_page_num})


### 마이페이지 시작
# 각 사용자의 프로필과 글을 모아볼 수 있는 공간(마이페이지)로 이동
@app.route('/user/<username>')
def user(username):
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        status = (username == payload["id"])  # 내 프로필이면 True, 다른 사람 프로필 페이지면 False

        user_info = db.users.find_one({"username": username}, {"_id": False})

        return render_template('user.html', user_info=user_info, status=status)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


# 개인정보 수정
@app.route('/update_profile', methods=['POST'])
def update_profile():
    token_receive = request.cookies.get('mytoken')
    AWS_ACCESS_KEY_ID = "AKIA6AVDKCZBAOTGDOHA"
    AWS_SECRET_ACCESS_KEY = "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"
    BUCKET_NAME = "gogumacat-bucket"
    s3 = boto3.client('s3',
                      aws_access_key_id=AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                      )

    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        username = payload["id"]
        userdata = db.users.find_one({"username": payload["id"]})
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

        db.posts.update_many({'username': username}, {'$set': {'nickname': name_receive}})

        if 'file_give' in request.files:
            file = request.files["file_give"]
            extension = file.filename.split('.')[-1]
            name = userdata['username']
            file_name = f'file-{name}'
            name = f'{file_name}.{extension}'
            print(name)
            # s3 파일 저장
            s3.put_object(
                ACL="public-read",
                Bucket=BUCKET_NAME,
                Body=file,
                Key='profile_pics/'+name,
                ContentType=file.content_type
            )
            # s3 파일 불러오기
            location = s3.get_bucket_location(Bucket=BUCKET_NAME)['LocationConstraint']
            image_url = f'https://{BUCKET_NAME}.s3.{location}.amazonaws.com/profile_pics/{name}'
            #db업데이트
            new_doc["profile_pic"] = image_url
        db.users.update_one({'username': username}, {'$set': new_doc})
        return jsonify({"result": "success", 'msg': '프로필을 업데이트했습니다.'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


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

    AWS_ACCESS_KEY_ID = "AKIA6AVDKCZBAOTGDOHA"
    AWS_SECRET_ACCESS_KEY = "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"
    BUCKET_NAME = "gogumacat-bucket"
    #s3 엑세스 키
    s3 = boto3.client('s3',
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                    )

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

        # 현재 시간 체크
        today = datetime.now()
        mytime = today.strftime('%Y-%m-%d-%H-%M-%S')

        # 파일 확장자 빼고 시간을 이름에 붙이기
        extension = file.filename.split('.')[-1]
        file_name = f'file-{mytime}'
        print(extension, file_name)
        name = f'{file_name}.{extension}'
        # s3 파일 저장
        s3.put_object(
            ACL="public-read",
            Bucket=BUCKET_NAME,
            Body=file,
            Key=name,
            ContentType=file.content_type
        )
        #s3 url 불러오기
        location = s3.get_bucket_location(Bucket=BUCKET_NAME)['LocationConstraint']
        image_url = f'https://{BUCKET_NAME}.s3.{location}.amazonaws.com/{name}'
        print(location)
        print(image_url)
        #DB에 저장
        doc = {
            'idx': idx,
            'username': username,
            'nickname': nickname,
            'title': title,
            'date': date,
            'price': price,
            'file': image_url,
            'content': content,
            'address': address,
            'like_count': 0,
            'file_name': name
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
    user = db.users.find_one({'username': post["username"]}, {'_id': False})

    post["like_count"] = db.likes.count_documents({"idx": int(idx)})
    post["like_by_me"] = bool(db.likes.find_one({"idx": int(idx), "username": payload['id']}))

    return render_template("post.html", post=post, user_info=user_info, user=user)


@app.route('/posts/<int:idx>/chat')
def chat(idx):
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    username = payload["id"]
    user_info = db.users.find_one({"username": username}, {"_id": False})
    post = db.posts.find_one({'idx': int(idx)}, {'_id': False})
    return render_template("chat.html", post=post, user_info=user_info, id=username)


def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(10)
        count += 1
        # socketio.emit('my_response',
        #               {'data': 'Server generated event', 'count': count})


@socketio.event
def my_event(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count'], 'type': 2})


@socketio.event
def join(message):
    join_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': '',
          'count': session['receive_count'], 'type': message['type']},
         to=message['room'])


@socketio.event
def leave(message):
    leave_room(message['room'])
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'In rooms: ' + ', '.join(rooms()),
          'count': session['receive_count'], 'type': 3})


@socketio.on('close_room')
def on_close_room(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response', {'data': '',
                         'count': session['receive_count']},
         to=message['room'])
    close_room(message['room'])


@socketio.event
def my_room_event(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    username = payload['id']
    user_info = db.users.find_one({"username": username}, {"_id": False})
    emit('my_response',
         {'data': message['data'], 'count': session['receive_count'], 'type': 1, 'name': user_info['nickname'],
          'image': user_info['profile_pic_real']},
         to=message['room'])


@socketio.event
def disconnect_request():
    @copy_current_request_context
    def can_disconnect():
        disconnect()

    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']},
         callback=can_disconnect)


@socketio.event
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)
    emit('my_response', {'data': '연결되었습니다.', 'count': 0, 'type': 2})


@socketio.on('disconnect')
def test_disconnect():
    print('Client disconnected', request.sid)


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



# 게시물 삭제
@app.route('/posts/delete', methods=['POST'])
def delete_post():
    idx = request.form.get('idx');
    # 해당 게시물 삭제
    db.posts.delete_one({"idx": int(idx)})
    # 해당 게시물에 좋아요를 누른 기록들 삭제
    db.likes.delete_many({'idx': int(idx)})

    return {"result": "success"}


# update페이지로 이동할 때 사용하는 함수
@app.route('/posting_update/<username>/<int:idx>')
def update_page(username, idx):
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        username_payload = payload["id"]
        user_info = db.users.find_one({"username": username_payload}, {"_id": False})
        # 현재가입된 값과 유저네임이 같지 않다면 home으로
        if (username_payload != username):
            return redirect(url_for("home"))

        post = db.posts.find_one({'idx': int(idx)}, {'_id': False})
        return render_template("posting_update.html", user_info=user_info, post=post)
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


@app.route('/user_post_update/<int:idx>', methods=['POST'])
def updating(idx):
    # 토큰확인
    AWS_ACCESS_KEY_ID = "AKIA6AVDKCZBAOTGDOHA"
    AWS_SECRET_ACCESS_KEY = "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"
    BUCKET_NAME = "gogumacat-bucket"
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        userdata = db.users.find_one({"username": payload["id"]})  # payload속 id 값 받기
        # 클라이언트 post 데이터 받기
        title = request.form['title_give']
        date = request.form['date_give']
        price = request.form['price_give']
        content = request.form['content_give']
        address = request.form['address_give']
        post = db.posts.find_one({'idx': int(idx)}, {'_id': False})

        try:
            # s3 엑세스 키
            s3 = boto3.client('s3',
                              aws_access_key_id=AWS_ACCESS_KEY_ID,
                              aws_secret_access_key=AWS_SECRET_ACCESS_KEY
                              )

            #파일 값 받아오기
            file = request.files['file_give']
            # 현재 시간 체크
            today = datetime.now()
            mytime = today.strftime('%Y-%m-%d-%H-%M-%S')

            # 파일 확장자 빼고 시간을 이름에 붙이기
            extension = file.filename.split('.')[-1]
            file_name = f'file-{mytime}'
            name = f'{file_name}.{extension}'
            # s3 파일 저장
            s3.put_object(
                ACL="public-read",
                Bucket=BUCKET_NAME,
                Body=file,
                Key=name,
                ContentType=file.content_type
            )
            # s3 url 불러오기
            location = s3.get_bucket_location(Bucket=BUCKET_NAME)['LocationConstraint']
            image_url = f'https://{BUCKET_NAME}.s3.{location}.amazonaws.com/{name}'
            print(image_url)
            db.posts.update_one({'idx': int(idx)}, {'$set': {'file': image_url}})
            db.posts.update_one({'idx': int(idx)}, {'$set': {'file_name': name}})

        except : pass



        if (post["title"] != title):  # 타이틀 업데이트
            db.posts.update_one({'idx': int(idx)}, {'$set': {'title': title}})

        if (post["date"] != date):  # 날짜 업데이트
            db.posts.update_one({'idx': int(idx)}, {'$set': {'date': date}})

        if (post["price"] != price):  # 가격 업데이트
            db.posts.update_one({'idx': int(idx)}, {'$set': {'price': price}})

        if (post["content"] != content):  # 내용 업데이트
            db.posts.update_one({'idx': int(idx)}, {'$set': {'content': content}})

        if (post["address"] != address):  # 주소 업데이트
            db.posts.update_one({'idx': int(idx)}, {'$set': {'address': address}})

        return jsonify({"result": "success", 'msg': '수정이 완료되었습니다.'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
