var geocoder = new kakao.maps.services.Geocoder();

var callback = function (result, status) {
    if (status === kakao.maps.services.Status.OK) {

        $('#address-tag').addClass("is-dark")
        $('#latest-tag').removeClass("is-dark")
        $('#like-tag').removeClass("is-dark")

        let address_dong = result[0].address.region_3depth_name

        $.ajax({
            type: "GET",
            url: `/search/myloc?address=${address_dong}&page=${page}`,
            data: {},
            success: function (response) {
                $("#card-box").empty();
                let posts = response["posts"];

                pagination(parseInt(response["last_page_num"]), page, "my_address")
                console.log("posts:", posts)

                for (let i = 0; i < posts.length; i++) {
                    make_post(posts[i]);
                }
            }
        });
    }
}

function find_location(new_page) {
    page = new_page
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(show_your_location, show_error_msg);
    } else {
        alert("위치 정보 사용을 동의해주세요.")
    }
}

function show_your_location(position) {
    var user_lat = position.coords.latitude;
    var user_lng = position.coords.longitude;
    geocoder.coord2Address(user_lng, user_lat, callback)
}

function show_error_msg(error) {
    switch (error.code) {
        case error.PERMISSION_DENIED:
            alert("이 문장은 사용자가 Geolocation API의 사용 요청을 거부했을 때 나타납니다!")
            break;
        case error.POSITION_UNAVAILABLE:
            alert("이 문장은 가져온 위치 정보를 사용할 수 없을 때 나타납니다!")
            break;
        case error.TIMEOUT:
            alert("이 문장은 위치 정보를 가져오기 위한 요청이 허용 시간을 초과했을 때 나타납니다!")
            break;
        case error.UNKNOWN_ERROR:
            alert("이 문장은 알 수 없는 오류가 발생했을 때 나타납니다!")
            break;
    }
}