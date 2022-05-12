let order = "latest"
let page = 1
$(document).ready(function () {
    order = "latest"
    page = 1
    listing(order, page);
});

function listing(new_order, new_page) {
    order = new_order
    page = new_page
    console.log(order, page)
    $.ajax({
        type: "GET",
        url: `/listing?order=${order}&page=${page}`,
        data: {},
        success: function (response) {
            $("#card-box").empty();
            let posts = response["posts"];

            pagination(parseInt(response["last_page_num"]), page, "main")
            console.log("posts:", posts)

            for (let i = 0; i < posts.length; i++) {
                make_post(posts[i]);
            }
        }
    });
}

function make_post(post) {
    let temp_html = `<div class="col" style="cursor: pointer;">
                                <div class="card h-100" id="card-${post['idx']}">
                                    <!--사진 수정-->
                                    <img src="${post['file']}" class="card-img-top image" onclick="location.href='/posts/${post['idx']}'">
                                    <div class="card-body">
                                        <h5 class="card-title" onclick="location.href='/posts/${post['idx']}'">${post['title']}</h5>
                                        <p class="card-text" style="font-weight: bold;">${post['price']}원</p>
                                        <p class="address-text">${post['address']}</p>
                                        <p class="card-text small-text">관심 ${post['like_count']}</p>
                                    </div>
                                </div>
                            </div>`
    $("#card-box").append(temp_html)
}

function searching(new_order, new_page) {
    order = new_order
    page = new_page
    let query = $('#search-box').val();
    if (query == "") {
        query = $("#query-text-box").val().split[" "][0];
    }
    if (query == "") {
        alert("검색어를 입력하세요");
        return;
    } else {
        $.ajax({
            type: "GET",
            url: `/search?query=${query}&order=${order}&page=${page}`,
            data: {},
            success: function (response) {
                $("#card-box").empty();
                let posts = response["posts"];
                pagination(parseInt(response["last_page_num"]), page, "search")
                for (let i = 0; i < posts.length; i++) {
                    make_post(posts[i], i);
                }

                $("#query-text-box").empty()
                $("#query-text-box").append(`"${query}" 검색내역 입니다.`)
                $("#query-text-box").removeClass("is-hidden")
            }
        })
    }
}

function pagination(last_page_num, page, type) {
    $("#pagination-list").empty()

    if (last_page_num == 1) {
        $("#page-box").addClass("is-hidden")
    }

    let temp_html = ""

    let start = page - 4

    if (start <= 0) {
        start = 1
    }

    let cnt = 0
    for (let i = start; i <= last_page_num; i++) {
        if (cnt > 9) {
            temp_html += `<li><span class="pagination-ellipsis">&hellip;</span></li>`
            break
        }
        if (page == i) {
            temp_html += `<li><a class="pagination-link is-current" area-current="page">${page}</a></li>`
        } else {
            if (type == "search") {
                temp_html += `<li><a class="pagination-link" onclick="searching(order,${i})">${i}</a></li>`
            } else if (type == "address") {
                temp_html += `<li><a class="pagination-link" onclick="search_by_address(order,${i})">${i}</a></li>`
            } else if (type == "my_address") {
                temp_html += `<li><a class="pagination-link" onclick="find_location(order,${i})">${i}</a></li>`
            } else {
                temp_html += `<li><a class="pagination-link" onclick="listing(order,${i})">${i}</a></li>`
            }
        }
        cnt += 1
    }

    $("#pagination-list").append(temp_html)
}

function click_sort_btn(order_type, page) {
    if ($("#query-text-box").hasClass("is-hidden") && $("#juso-search-btn").hasClass("is-hidden")) {
        listing(order_type, page)
    } else if ($("#query-text-box").hasClass("is-hidden")) {
        search_by_address(order_type, page)
    } else {
        searching(order_type, page)
    }

    if (order_type == "latest") {
        $('#latest-tag').addClass("is-dark")
        $('#like-tag').removeClass("is-dark")
        $('#address-tag').removeClass("is-dark")
    } else {
        $('#like-tag').addClass("is-dark")
        $('#latest-tag').removeClass("is-dark")
        $('#address-tag').removeClass("is-dark")
    }
}

function get_gu(si) {
    $("#gu-box").addClass("is-hidden")
    $("#dong-box").addClass("is-hidden")
    $("#juso-search-btn").addClass("is-hidden")
    $.ajax({
        type: "GET",
        url: `/get_gu?si=${si}`,
        data: {},
        success: function (response) {
            if (response["gu"] == "세종특별자치시") {
                get_dong("세종특별자치시")
                return
            }
            $("#gu-select").empty();
            let gu = response["gu"];
            let temp_html = "<option>동네를 선택하세요</option>"
            for (let i = 0; i < gu.length; i++) {
                temp_html += `<option value="${gu[i]}">${gu[i]}</option>`
            }
            $("#gu-select").append(temp_html)
            $("#gu-box").removeClass("is-hidden")
        }
    });
}

function get_dong(gu) {
    $.ajax({
        type: "GET",
        url: `/get_dong?gu=${gu}`,
        data: {},
        success: function (response) {
            $("#dong-select").empty();
            let dong = response["dong"];
            let temp_html = "<option>동을 선택하세요</option>"
            for (let i = 0; i < dong.length; i++) {
                temp_html += `<option value="${dong[i]}">${dong[i]}</option>`
            }
            $("#dong-select").append(temp_html)
            $("#dong-box").removeClass("is-hidden")
        }
    });
}

function search_by_address(new_order, new_page) {
    order = new_order
    page = new_page
    let si = $("#si-select").val()
    let gu = $("#gu-select").val()
    let dong = $("#dong-select").val()
    $.ajax({
        type: "GET",
        url: `/search/address?si=${si}&gu=${gu}&dong=${dong}&order=${order}&page=${page}`,
        data: {},
        success: function (response) {
            $("#card-box").empty();
            let posts = response["posts"];
            pagination(parseInt(response["last_page_num"]), page, "address")
            for (let i = 0; i < posts.length; i++) {
                make_post(posts[i], i);
            }
        }
    });
}