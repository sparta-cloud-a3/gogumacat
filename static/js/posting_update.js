

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
        content += '        <img src="/info_image.png" style="object-fit: fill" >';
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


//캘린더 함수
function calender_select() {
    $(function () {
        $('#calender').daterangepicker({ //한글로 번역
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

