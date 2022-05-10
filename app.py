from flask import Flask, render_template, jsonify, request, redirect, url_for
from pymongo import MongoClient

import jwt
import hashlib
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

import math

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
def listing_page():
    order = request.args.get('order')
    # default는 1이고 type은 int
    page = request.args.get('page', 1, type=int)
    # 한 페이지당 10개 보여줌
    limit = 9
    if order == 'like':
        posts = list(db.posts.find({},{'_id': False}).sort('liked', -1).skip((page-1)*limit).limit(limit))
    else:
        posts = list(db.posts.find({}, {'_id': False}).sort('_id', -1).skip((page - 1) * limit).limit(limit))

    total_count = db.posts.estimated_document_count({})
    last_page_num = math.ceil(total_count/limit)

    return jsonify({'posts': posts, 'limit':limit, 'page': page, 'last_page_num': last_page_num })

@app.route('/search', methods=['GET'])
def searching_page():
    query_receive = request.args.get('query')
    order = request.args.get('order')
    # default는 1이고 type은 int
    page = request.args.get('page', 1, type=int)
    # 한 페이지당 10개 보여줌
    limit = 3

    if order == 'like':
        posts = list(db.posts.find( { '$or': [ {'title': {'$regex': query_receive}}, {'content': {'$regex': query_receive}} ] }, {'_id': False}).sort('liked', -1).skip((page-1)*limit).limit(limit))
    else:
        posts = list(
            db.posts.find({'$or': [{'title': {'$regex': query_receive}}, {'content': {'$regex': query_receive}}]},
                          {'_id': False}).sort('_id', -1).skip((page - 1) * limit).limit(limit))

    total_count = len(list(db.posts.find({'$or': [{'title': {'$regex': query_receive}}, {'content': {'$regex': query_receive}}]},{'_id': False})))
    last_page_num = math.ceil(total_count / limit)
    print(total_count)
    return jsonify({"query": query_receive, "posts": posts, 'limit':limit, 'page': page, 'last_page_num': last_page_num })


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
            comments = list(db.comments.find({"username":username_receive},{'_id': False}).sort('_id', -1).limit(9))
            reviews = ""
            likes = list(db.likes.find({"username":username_receive},{'_id': False}).sort('_id', -1).limit(9))
            for i in range(len(comments)):
                comments[i] = db.posts.find({'post_id': comments[i]['post_id']},{'_id': False}).sort("date", -1).limit(9)
            for i in range(len(likes)):
                likes[i] = db.posts.find({'post_id': likes[i]['post_id']},{'_id': False}).sort("date", -1).limit(9)

        return jsonify({'posts': posts, 'comments':comments, 'reviews':reviews, 'likes':likes})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect(url_for("home"))

#유저 개인의 물품 등록페이지 띄우기
@app.route('/posting/<username>')
def post_page(username):
    token_receive = request.cookies.get('mytoken')
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    username = payload["id"]
    user_info = db.users.find_one({"username": username}, {"_id": False})

    return render_template("posting.html", user_info=user_info )

# 등록할 내용 DB저장
@app.route('/user_post',methods=['POST'])
def posting():
    print(request.form)
#DB 포스트 값에 고유번호 부여하기
    if 0 >= db.posts.estimated_document_count():
        idx = 1
    else:
        idx = list(db.posts.find({}, sort=[('_id', -1)]).limit(1))[0]['idx'] + 1
#토큰확인
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        userdata = db.users.find_one({"username": payload["id"]})  # payload속 id 값 받기
# 클라이언트 post 데이터 받기
        username = userdata['username']
        nickname = userdata['nickname']
        print(username,nickname)
        title = request.form['title_give']
        date = request.form['date_give']
        price = request.form['price_give']
        file = request.files['file_give']
        content = request.form['content_give']
        address = request.form['address_give']
        print(title,date,price,file,content,address)

    #현재 시각 체크하기
        today = datetime.now()
        mytime = today.strftime('%Y-%m-%d-%H-%M-%S')

    #파일 확장자 빼고 시간을 이름에 붙이기
        extension = file.filename.split('.')[-1]
        filename = f'file-{mytime}'
        print(extension,filename)
    #static폴더에 파일 저장
        save_to = f'static/{filename}.{extension}'
        file.save(save_to)
    #데이터 DB에 저장하기
        doc = {
            'idx': idx,
            'username': username,
            'nickname' : nickname,
            'title': title,
            'date' : date,
            'price': price,
            'file' : f'{filename}.{extension}',
            'content':content,
            'address':address,
            'like_count': ""
        }
        print(doc)
        db.posts.insert_one(doc)
        return jsonify({"result": "success", 'msg': '등록이 완료되었습니다.'})
    except (jwt.ExpiredSignatureError, jwt.exceptions.DecodeError):
        return redirect()










if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)