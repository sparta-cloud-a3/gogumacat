function toggle_like(idx) {

    if ($("#heart").hasClass("fa-solid")) {
        $.ajax({
            type: "POST",
            url: "/update_like",
            data: {
                idx_give: idx,
                action_give: "unlike"
            },
            success: function (response) {
                console.log("unlike")
                $("#heart").addClass("fa-regular").removeClass("fa-solid")
                $("#heart-count-box").text(num2str(response["count"]))
            }
        })
    } else {
        $.ajax({
            type: "POST",
            url: "/update_like",
            data: {
                idx_give: idx,
                action_give: "like"
            },
            success: function (response) {
                console.log("like")
                $("#heart").addClass("fa-solid").removeClass("fa-regular")
                $("#heart-count-box").text(num2str(response["count"]))
            }
        })
    }
}

function num2str(count) {
    if (count > 10000) {
        return parseInt(count / 1000) + "k"
    }
    if (count > 500) {
        return parseInt(count / 100) / 10 + "k"
    }
    if (count == 0) {
        return ""
    }
    return count
}