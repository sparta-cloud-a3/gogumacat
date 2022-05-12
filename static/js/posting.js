$(document).ready(function () {
    fileupload()
    calendar_select()
})

//파일 업로드 시 제목 띄우기
function fileupload() {
    const fileInput = document.querySelector('#file-js-example input[type=file]');

    fileInput.onchange = () => {
        if (fileInput.files.length > 0) {
            const fileName = document.querySelector('#file-js-example .file-name');
            fileName.textContent = fileInput.files[0].name;
        }
    }
}

// 이미지 업로드 및 업로드한 이미지 미리보기
function img_up() {
    $('#img').on('change', function () {
        ext = $(this).val().split('.').pop().toLowerCase(); //확장자
        //배열에 추출한 확장자가 존재하는지 체크
        if ($.inArray(ext, ['png', 'jpg', 'jpeg']) == -1) {
            alert("jpg,jpeg,png 이미지만 사용 가능합니다.")
            const fileName = document.querySelector('#file-js-example .file-name');
            fileName.textContent = "";//스팬 값 초기화
            $("#image_preview").toggleClass("is-hidden")
        } else {
            file = $('#img').prop("files")[0];
            blobURL = window.URL.createObjectURL(file);
            $('#image_preview img').attr('src', blobURL);
            $('#image_preview').slideDown(); //업로드한 이미지 미리보기
            $(this).slideUp(); //파일 양식 감춤
            $("#image_preview").removeClass("is-hidden")
        }
    });
}


//지도 띄우는 코드
function map() {
    let local = $('#local_address').val()
    //주소 확인
    if (local == "") {
        $("#local_warning").addClass("is-danger").removeClass("is-hidden")
    } else {
        $('#local_warning').addClass("is-hidden")
        $("#map").toggleClass("is-hidden")
        //지도 작동
        var mapContainer = document.getElementById('map'), // 지도를 표시할 div
            mapCenter = new kakao.maps.LatLng(33.5563, 126.7958), // 지도의 중심좌표
            mapOption = {
                center: mapCenter, // 지도의 중심좌표
                level: 3 // 지도의 확대 레벨
            };

        var map = new kakao.maps.Map(mapContainer, mapOption);

        var geocoder = new kakao.maps.services.Geocoder();

        // 커스텀 오버레이에 표시할 내용입니다
        // HTML 문자열 또는 Dom Element 입니다
        var content = '<div class="overlay_info">';
        content += '    <a><strong>여기서 만나요!</strong></a>';
        content += '    <div class="desc">';
        content += '        <img src="/static/info_image.png" style="object-fit: fill" >';
        content += `        <span class="address">${local}</span>`;
        content += '    </div>';
        content += '</div>';

        geocoder.addressSearch(local, function (result, status) {
            if (status === kakao.maps.services.Status.OK) {
                // 커스텀 오버레이가 표시될 위치입니다
                var position = new kakao.maps.LatLng(result[0].y, result[0].x);

                // 커스텀 오버레이를 생성합니다
                var mapCustomOverlay = new kakao.maps.CustomOverlay({
                    position: position,
                    content: content,
                    xAnchor: 0.5, // 커스텀 오버레이의 x축 위치입니다. 1에 가까울수록 왼쪽에 위치합니다. 기본값은 0.5 입니다
                    yAnchor: 1.1 // 커스텀 오버레이의 y축 위치입니다. 1에 가까울수록 위쪽에 위치합니다. 기본값은 0.5 입니다
                });

                // 커스텀 오버레이를 지도에 표시합니다
                mapCustomOverlay.setMap(map);

                map.setCenter(position);
            }
        });
    }
}


//주소 검색하기
function local_search() {
    new daum.Postcode({
        oncomplete: function (data) {
            var jibun = data.autoJibunAddress
            // 주소 정보를 해당 필드에 넣는다.
            if (jibun == "") {
                var juso = data.jibunAddress
                document.getElementById("local_address").value = juso
            } else {
                document.getElementById("local_address").value = jibun
            }

        }
    }).open();
}

//포스팅하기
function posting() {
    //input값 가져오기
    let title = $('#title').val()
    let date = $('#calendar').val()
    let price = $('#price').val()
    let content = $('#content').val()
    let address = $('#local_address').val()
    let file = $('#img')[0].files[0]
    //form 데이터 넣기
    let form_data = new FormData()
    form_data.append("title_give", title)
    form_data.append("file_give", file)
    form_data.append("date_give", date)
    form_data.append("price_give", price)
    form_data.append("content_give", content)
    form_data.append("address_give", address)
    //동작 조건 만들기
    if (title == "") {
        alert("제목,물품명을 입력해주세요")
    } else if (date == "") {
        alert("대여 기간을 입력해주세요")
    } else if (price == "") {
        alert("가격을 입력해주세요")
    } else if (file == undefined) {
        alert("제품 사진을 첨부해주세요")
    } else if (content == "") {
        alert("내용을 적어주세요")
    } else if (address == "") {
        alert("주소를 입력해주세요")
    } else {
        //포스팅 aJax 콜
        $.ajax({
            type: "POST",
            url: "/user_post",
            data: form_data,
            cache: false,
            contentType: false,
            processData: false,
            enctype: "multipart/form-data",
            success: function (response) {
                if (response["result"] == "success") {
                    alert(response["msg"])
                    console.log(response)
                    window.location.href = '/'
                } else {
                    alert("내용을 다시 확인해 주세요")
                }
            }
        })
    }
}

//캘린더 함수
function calendar_select() {
    $(function () {
        $('#calendar').daterangepicker({ //한글로 번역
            "locale": {
                "format": "YYYY-MM-DD",
                "separator": " ~ ",
                "fromLabel": "From",
                "toLabel": "To",
                "customRangeLabel": "Custom",
                "weekLabel": "W",
                "daysOfWeek": ["월", "화", "수", "목", "금", "토", "일"],
                "monthNames": ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"],
                "firstDay": 1,
            },
            autoUpdateInput: false,
            autoApply: true,
            "drops": "down",

        }, function (start, end, label) {
        });
    });
    $('input[name="datefilter"]').on('apply.daterangepicker', function (ev, picker) {
        $(this).val(picker.startDate.format('MM/DD/YYYY') + ' - ' + picker.endDate.format('MM/DD/YYYY'));
    });

    $('input[name="datefilter"]').on('cancel.daterangepicker', function (ev, picker) {
        $(this).val('');
    })
}

//가격정보 숫자만 받도록
function price(t) {
    // 콤마 빼고
    var x = t.value
    x = x.replace(/,/gi, '');
    // 숫자 정규식 확인
    var regexp = /^[0-9]*$/;
    if (!regexp.test(x)) {
        $(t).val("");
        $("#price_warning").removeClass("is-hidden")
    } else {
        x = x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        $(t).val(x);
        $("#price_warning").addClass("is-hidden")
    }
}

