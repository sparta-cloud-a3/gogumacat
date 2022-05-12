function sign_out() {
    $.removeCookie('mytoken', {path: '/'});
    alert('로그아웃!')
    window.location.href = "/login"
}

function get_posts(username) {
    $.ajax({
        type: "GET",
        url: `/get_posts?username_give=${username}`,
        data: {},
        success: function (response) {
            $("#card-box-post").empty();
            $("#card-box-comment").empty();
            $("#card-box-review").empty();
            $("#card-box-like").empty();
            let posts = response["posts"];
            let comments = response["comments"];
            let reviews = response["reviews"];
            let likes = response["likes"];
            for (let i = 0; i < posts.length; i++) {
                make_post(posts[i], "post");
            }
            for (let i = 0; i < comments.length; i++) {
                make_post(comments[i], "comment");
            }
            for (let i = 0; i < likes.length; i++) {
                make_post(likes[i], "like");
            }
        }
    });
}

function make_post(post, type) {
    let temp_html = `<div class="col" style="cursor: pointer">
                                <div class="card h-100" id="card-${post['idx']}">
                                    <!--사진 수정-->
                                    <img src="/static/post_pic/${post['file']}" class="card-img-top image" onclick="location.href='/posts/${post['idx']}'">
                                    <div class="card-body">
                                        <h5 class="card-title" onclick="location.href='/posts/${post['idx']}'">${post['title']}</h5>
                                        <p class="card-text" style="font-weight: bold;">${post['price']}원</p>
                                        <p class="address-text">${post['address']}</p>
                                        <p class="card-text small-text">관심 ${post['like_count']}</p>
                                    </div>
                                </div>
                            </div>`
    $(`#card-box-${type}`).append(temp_html)
}


function update_profile(old_nickname) {
    let name = $('#input-nickname').val()
    let file = $('#input-pic')[0].files[0]
    let about = $("#textarea-about").val()
    let password = $('#input-password').val()
    let password2 = $("#input-password2").val()
    let address = $('#input-address').val()

    if (name == old_nickname) {
        console.log(old_nickname)
    } else if ($("#help-nickname").hasClass("is-danger")) {
        alert("닉네임을 다시 확인해주세요.")
        return;
    } else if (!$("#help-nickname").hasClass("is-success")) {
        alert("닉네임 중복확인을 해주세요.")
        return;
    }

    if (password == "") {
        $("#help-password").text("비밀번호를 입력해주세요.").removeClass("is-safe").addClass("is-danger")
        $("#input-password").focus()
    } else if (!is_password(password)) {
        $("#help-password").text("비밀번호의 형식을 확인해주세요. 영문과 숫자 필수 포함, 특수문자(!@#$%^&*) 사용가능 8-20자").removeClass("is-safe").addClass("is-danger")
        $("#input-password").focus()
    } else {
        $("#help-password").text("사용할 수 있는 비밀번호입니다.").removeClass("is-danger").addClass("is-success")
    }

    if (password2 == "") {
        $("#help-password2").text("비밀번호를 입력해주세요.").removeClass("is-safe").addClass("is-danger")
        $("#input-password2").focus()
        return;
    } else if (password2 != password) {
        $("#help-password2").text("비밀번호가 일치하지 않습니다.").removeClass("is-safe").addClass("is-danger")
        $("#input-password2").focus()
        return;
    } else {
        $("#help-password2").text("비밀번호가 일치합니다.").removeClass("is-danger").addClass("is-success")
    }

    if (address == "") {
        $("#help-address").text("주소를 입력해주세요.").removeClass("is-safe").addClass("is-danger")
        $("#input-address").focus()
        return;
    }


    let form_data = new FormData()
    form_data.append("file_give", file)
    form_data.append("name_give", name)
    form_data.append("about_give", about)
    form_data.append("address_give", address)
    form_data.append("password_give", password)

    $.ajax({
        type: "POST",
        url: "/update_profile",
        data: form_data,
        cache: false,
        contentType: false,
        processData: false,
        success: function (response) {
            if (response["result"] == "success") {
                alert(response["msg"])
                window.location.reload()
            }
        }
    });
}

function is_password(asValue) {
    var regExp = /^(?=.*\d)(?=.*[a-zA-Z])[0-9a-zA-Z!@#$%^&*]{8,20}$/;
    return regExp.test(asValue);
}

function check_dup_nick() {
    let nickname = $("#input-nickname").val()

    if (nickname == "") {
        $("#help-nickname").text("닉네임을 입력해주세요.").removeClass("is-safe").addClass("is-danger")
        $("#input-nickname").focus()
        return;
    }
    $("#help-nickname").addClass("is-loading")
    $.ajax({
        type: "POST",
        url: "/sign_up/check_dup_nick",
        data: {
            nickname_give: nickname
        },
        success: function (response) {

            if (response["exists"]) {
                $("#help-nickname").text("이미 존재하는 닉네임입니다.").removeClass("is-safe").addClass("is-danger")
                $("#input-nickname").focus()
            } else {
                $("#help-nickname").text("사용할 수 있는 닉네임입니다.").removeClass("is-danger").addClass("is-success")
            }
            $("#help-nickname").removeClass("is-loading")

        }
    });
}

function check_pw() {
    let pw = $("#input-check-pw").val();

    if (pw == "") {
        $("#help-check-password").text("비밀번호를 입력해주세요.")
        $("#input-check-pw").focus()
        return
    } else {
        $("#input-check-pw").val("")
    }

    $.ajax({
        type: "POST",
        url: "/check",
        data: {
            password_give: pw
        },
        success: function (response) {
            if (response["result"]) {
                $("#help-check-password").removeClass("is-danger")
                $("#help-check-password").text("비밀번호를 입력해주세요.")
                $("#modal-check-pw").removeClass("is-active")
                $("#modal-edit").addClass("is-active")
            } else {
                $("#help-check-password").text("비밀번호가 틀렸습니다.")
                $("#help-check-password").addClass("is-danger")
                $("#input-check-pw").val("")
            }
        }
    });
}

function juso() {
    new daum.Postcode({
        oncomplete: function (data) {
            var roadAddr = data.roadAddress; // 도로명 주소 변수
            var extraRoadAddr = ''; // 참고 항목 변수

            if (data.bname !== '' && /[동|로|가]$/g.test(data.bname)) {
                extraRoadAddr += data.bname;
            }
            if (data.buildingName !== '' && data.apartment === 'Y') {
                extraRoadAddr += (extraRoadAddr !== '' ? ', ' + data.buildingName : data.buildingName);
            }
            if (extraRoadAddr !== '') {
                extraRoadAddr = ' (' + extraRoadAddr + ')';
            }

            newjuso = data.jibunAddress.split(' ').slice(0, -1).join(' ')
            document.getElementById("input-address").value = newjuso // 지번주소
        }
    }).open();
}