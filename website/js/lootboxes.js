function calculateBoxes(table_name) {
    const table = document.getElementById(`table-${table_name}`);
    const elements = table.getElementsByTagName('input');
    var total = 0;
    for (let i = 0; i < elements.length; i++) {
        var element = elements[i];
        var chance = parseFloat(element.getAttribute('chance'));
        var amount = parseInt(element.value);
        var value = amount / chance;
        if (total < value) {
            total = value;
        }
    }
    for (let i = 0; i < elements.length; i++) {
        var element = elements[i];
        var chance = parseFloat(element.getAttribute('chance'));
        var amount = Math.round(total * chance);
        element.value = amount;
    }
    document.getElementById(`table-value-${table_name}`).innerHTML = Math.round(total);
}

function clearBoxes(table_name) {
    const table = document.getElementById(`table-${table_name}`);
    const elements = table.getElementsByTagName('input');
    var total = 0;
    for (let i = 0; i < elements.length; i++) {
        var element = elements[i];
        element.value = 0;
    }
    document.getElementById(`table-value-${table_name}`).innerHTML = Math.round(total);
}