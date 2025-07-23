function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

$(document).ready(function () {
    var currentUrl = window.location.href;
    $('.nav-link').each(function () {
        if (this.href === currentUrl) {
            $(this).closest('.nav-item').addClass('active');
        }
    });

    $('.dropdown-item').each(function () {
        if (this.href === currentUrl) {
            $(this).addClass('active');
            $(this).closest('.nav-item.dropdown').addClass('active');
        }
    });
});


function initializeDataTable(selector, columnDefs = []) {
    $(selector).DataTable({
        responsive: true,
        pageLength: 5,
        lengthMenu: [
            [5, 10, 20, -1],
            [5, 10, 20, 'All']
        ],
        autoWidth: false,
        language: {
            paginate: {
                next: '❯',
                previous: '❮'
            }
        },
        columnDefs: columnDefs
    });
}

// Function to determine the display text for the table number
function getTableDisplayText(tableNumber) {
    if (tableNumber === 44) {
        return "內";
    } else if (tableNumber === 45) {
        return "A";
    } else if (tableNumber === 46) {
        return "外帶";
    } else {
        return `${tableNumber}`;
    }
}
