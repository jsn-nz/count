document.getElementById("incomeForm").addEventListener("submit", function(event) {
    event.preventDefault();

    incomeValue = parseFloat(document.getElementById("incomeInput").value);
    const timePeriodSelected = document.getElementById('timePeriodSelect').value;
    const kiwisaverChecked = document.getElementById("kiwisaverCheckbox").checked;
    const studentLoanCheckbox = document.getElementById("studentLoanCheckbox").checked;
    const casualCheckbox = document.getElementById("casualCheckbox").checked;
    var kiwisaverValue = document.getElementById('kiwiSaverValue').value;
    var hoursValue = document.getElementById('hoursValue').value;
    var holidayPayValue = document.getElementById('holidayPayValue').value;

    if (isNaN(incomeValue)) {
        $('#error').modal('show');
        return;
    }

    if (incomeValue < 0) {
        $('#error').modal('show');
        return;
    }

    if (casualCheckbox) {
        incomeValue += incomeValue * (holidayPayValue/100);
    }

    $('#anchorLink').trigger('click');

    if (timePeriodSelected == "Hour") {
        incomeValue *= hoursValue*52;
    } else if (timePeriodSelected == "Week") {
        incomeValue *= 52;
    } else if (timePeriodSelected == "Fortnight") {
        incomeValue *= 26;
    } else if (timePeriodSelected == "Month") {
        incomeValue *= 12;
    }

    const taxAmount = calculateIncomeTax(incomeValue);
    const kiwiSaverDeduction = kiwisaverChecked ? incomeValue * (kiwisaverValue * 0.01) : 0;
    const studentLoanRepaymentThreshold = 24128;
    const studentLoanDeduction = studentLoanCheckbox && incomeValue > studentLoanRepaymentThreshold ? (incomeValue - studentLoanRepaymentThreshold) * 0.12 : 0;
    const accDeduction = calculateAccDeduction(incomeValue);
    const takeHomePay = incomeValue - taxAmount - kiwiSaverDeduction - studentLoanDeduction - accDeduction;

    updateDisplayValues({
        gross: incomeValue,
        tax: taxAmount,
        acc: accDeduction,
        kiwisaver: kiwiSaverDeduction,
        studentLoan: studentLoanDeduction,
        takeHome: takeHomePay
    });

    let taxcode = "M"; 
    if (studentLoanCheckbox) {
        taxcode = "M SL"; 
    }
    const takeHomePayGross = formatNumberWithCommas((takeHomePay / incomeValue) * 100) + "%";
    const takeHomePayWeek = "$" + formatNumberWithCommas(takeHomePay / 52);

    generatePieChart(taxAmount, kiwiSaverDeduction, studentLoanDeduction, accDeduction, takeHomePay, taxcode, takeHomePayGross, takeHomePayWeek);
});



function calculateIncomeTax(income) {
    let tax;
    if (income <= 15600) {
        tax = income * 0.105;
    } else if (income <= 53500) {
        tax = 15600 * 0.105 + (income - 15600) * 0.175;
    } else if (income <= 78100) {
        tax = 15600 * 0.105 + (53500 - 15600) * 0.175 + (income - 53500) * 0.3;
    } else if (income <= 180000) {
        tax = 15600 * 0.105 + (53500 - 15600) * 0.175 + (78100 - 53500) * 0.3 + (income - 78100) * 0.33;
    } else {
        tax = 15600 * 0.105 + (53500 - 15600) * 0.175 + (78100 - 53500) * 0.3 + (180000 - 78100) * 0.33 + (income - 180000) * 0.39;
    }
    return tax;
}

function calculateAccDeduction(incomeValue) {
    const accDeductionRate = 1.6;
    const accIncomeCap = 139384;

    return (Math.min(incomeValue, accIncomeCap) * accDeductionRate) / 100;
}

function formatNumberWithCommas(number, decimalPlaces = 2) {
    return new Intl.NumberFormat('en-US', {
        style: 'decimal',
        minimumFractionDigits: decimalPlaces,
        maximumFractionDigits: decimalPlaces
    }).format(number);
}

function updateDisplayValues(values) {
    const periods = {
        hour: 52 * 40, // Assuming 40 hours per week
        week: 52,
        fortnight: 26,
        month: 12,
        year: 1,
    };

    for (let period in periods) {
        document.getElementById(`grossPay${capitalizeFirstLetter(period)}`).textContent = formatNumberWithCommas(values.gross / periods[period]);
        document.getElementById(`payePer${capitalizeFirstLetter(period)}`).textContent = formatNumberWithCommas(values.tax / periods[period]);
        document.getElementById(`accPer${capitalizeFirstLetter(period)}`).textContent = formatNumberWithCommas(values.acc / periods[period]);
        document.getElementById(`kiwisaverPer${capitalizeFirstLetter(period)}`).textContent = formatNumberWithCommas(values.kiwisaver / periods[period]);
        document.getElementById(`studentLoanPer${capitalizeFirstLetter(period)}`).textContent = formatNumberWithCommas(values.studentLoan / periods[period]);
        document.getElementById(`takeHomePayPer${capitalizeFirstLetter(period)}`).textContent = formatNumberWithCommas(values.takeHome / periods[period]);
    }
}

let myPieChart;

function generatePieChart(taxAmount, kiwiSaverDeduction, studentLoanDeduction, accDeduction, takeHomePay, taxcode, takeHomePayGross, takeHomePayWeek) {
    if (myPieChart) {
        myPieChart.destroy();
    }

    document.querySelector(".result-container").style.display = "flex";

    let ctx = document.getElementById('incomeBreakdownChart').getContext('2d');
    myPieChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: ["PAYE", "Kiwisaver", "Student Loan", "ACC", "Take Home Pay"],
            datasets: [{
                data: [taxAmount, kiwiSaverDeduction, studentLoanDeduction, accDeduction, takeHomePay],
                backgroundColor: ["#ff5733", "#f9c74f", "#90be6d", "#f8961e", "#577590"]
            }]
        }
    });

    document.getElementById("taxcode").textContent = taxcode;
    document.getElementById("takeHomePayGross").textContent = takeHomePayGross;
    document.getElementById("takeHomePayWeek").textContent = takeHomePayWeek;
}

function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

$(document).ready(function(){
    $('a[href^="#"]').on('click', function(event) {
        var target = $(this.getAttribute('href'));
        if(target.length) {
            event.preventDefault();
            $('html, body').stop().animate({
                scrollTop: target.offset().top
            }, 1000);
        }
    });
});

document.getElementById('moreLink').addEventListener('click', function(e) {
    e.preventDefault();
    var moreOptions = document.getElementById('moreOptions');
    
    if (!moreOptions.classList.contains('visible')) {
        moreOptions.classList.add('visible');
    } else {
        moreOptions.classList.remove('visible');
        hoursOptions.classList.remove('visible');
        kiwisaverOptions.classList.remove('visible');
        holidayPayOptions.classList.remove('visible');
    }
});

document.getElementById('hoursLink').addEventListener('click', function(e) {
    e.preventDefault();
    var hoursOptions = document.getElementById('hoursOptions');
    var kiwisaverOptions = document.getElementById('kiwisaverOptions');
    var holidayPayOptions = document.getElementById('holidayPayOptions');

    if (!hoursOptions.classList.contains('visible')) {
        hoursOptions.classList.remove('instant-hide');
        hoursOptions.classList.add('visible');
    } else {
        hoursOptions.classList.add('instant-hide');
        hoursOptions.classList.remove('visible');
    }
    kiwisaverOptions.classList.add('instant-hide');
    kiwisaverOptions.classList.remove('visible');
    holidayPayOptions.classList.add('instant-hide');
    holidayPayOptions.classList.remove('visible');
});

document.getElementById('kiwisaverLink').addEventListener('click', function(e) {
    e.preventDefault();
    var kiwisaverOptions = document.getElementById('kiwisaverOptions');
    var hoursOptions = document.getElementById('hoursOptions');
    var holidayPayOptions = document.getElementById('holidayPayOptions');
    
    if (!kiwisaverOptions.classList.contains('visible')) {
        kiwisaverOptions.classList.remove('instant-hide');
        kiwisaverOptions.classList.add('visible');
    } else {
        kiwisaverOptions.classList.add('instant-hide');
        kiwisaverOptions.classList.remove('visible');
    }
    hoursOptions.classList.add('instant-hide');
    hoursOptions.classList.remove('visible');
    holidayPayOptions.classList.add('instant-hide');
    holidayPayOptions.classList.remove('visible');
});

document.getElementById('holidayPayLink').addEventListener('click', function(e) {
    e.preventDefault();
    var holidayPayOptions = document.getElementById('holidayPayOptions');
    var hoursOptions = document.getElementById('hoursOptions');
    var kiwisaverOptions = document.getElementById('kiwisaverOptions');
    
    if (!holidayPayOptions.classList.contains('visible')) {
        holidayPayOptions.classList.remove('instant-hide');
        holidayPayOptions.classList.add('visible');
    } else {
        holidayPayOptions.classList.add('instant-hide');
        holidayPayOptions.classList.remove('visible');
    }
    hoursOptions.classList.add('instant-hide');
    hoursOptions.classList.remove('visible');
    kiwisaverOptions.classList.add('instant-hide');
    kiwisaverOptions.classList.remove('visible');
});
