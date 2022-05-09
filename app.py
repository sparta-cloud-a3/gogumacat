from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.gogumacat


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/listing', methods=['GET'])
def listing():
    order = request.args.get('order')
    print(order)
    if order == "like":
        posts = list(db.posts.find({}, {'_id': False}).sort('liked', -1))
    else:
        posts = list(db.posts.find({}, {'_id': False}).sort('_id', -1))

    return jsonify({"posts":posts})

@app.route('/posts/<int:id>')
def give_post(id):
    post = db.posts.find_one({'post_id': id}, {'_id': False})

    return render_template('post.html', post=post)

@app.route('/search', methods=['GET'])
def search_listing():
    query_receive = request.args.get('query')
    posts = list(db.posts.find( { '$or': [ {'title': {'$regex': query_receive}}, {'content': {'$regex': query_receive}} ] }, {'_id': False}))

    return jsonify({"query": query_receive, "posts": posts})



if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)