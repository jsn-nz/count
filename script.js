let initialHourlyRate;

class IncomeCalculator {
    constructor(params) {
        this.incomeValue = params.incomeValue;
        this.hoursValue = params.hoursValue;
        this.timePeriodSelected = params.timePeriodSelected;
        this.kiwisaverChecked = params.kiwisaverChecked;
        this.studentLoanChecked = params.studentLoanChecked;
        this.casualChecked = params.casualChecked;
        this.kiwisaverValue = params.kiwisaverValue;
        this.holidayPayValue = params.holidayPayValue;
        this.incomeAnnual = 0;
    }

    calculateAnnualIncome() {
        let incomeValue = this.incomeValue;
        let hoursValue = this.hoursValue;

        switch (this.timePeriodSelected) {
            case "Hour":
                incomeValue *= hoursValue * 52;
                initialHourlyRate = undefined;
                break;
            case "Week":
                incomeValue *= 52;
                initialHourlyRate = undefined;
                break;
            case "Fortnight":
                incomeValue *= 26;
                initialHourlyRate = undefined;
                break;
            case "Month":
                incomeValue *= 12;
                initialHourlyRate = undefined;
                break;
            case "Year":
                if (typeof initialHourlyRate === 'undefined') {
                    initialHourlyRate = incomeValue / (52 * hoursValue);
                } else {
                    incomeValue = initialHourlyRate * (52 * hoursValue);
                }
                break;
            default:
                break;
        }

        if (this.casualChecked) {
            incomeValue += incomeValue * (this.holidayPayValue / 100);
        }

        this.incomeAnnual = incomeValue;
    }

    calculateIncomeTax() {
        let income = this.incomeAnnual;
        let tax;

        if (income <= 15600) {
            tax = income * 0.105;
        } else if (income <= 53500) {
            tax = 15600 * 0.105 + (income - 15600) * 0.175;
        } else if (income <= 78100) {
            tax = 15600 * 0.105 + (53500 - 15600) * 0.175 + (income - 53500) * 0.30;
        } else if (income <= 180000) {
            tax = 15600 * 0.105 + (53500 - 15600) * 0.175 + (78100 - 53500) * 0.30 + (income - 78100) * 0.33;
        } else {
            tax = 15600 * 0.105 + (53500 - 15600) * 0.175 + (78100 - 53500) * 0.30 + (180000 - 78100) * 0.33 + (income - 180000) * 0.39;
        }

        return tax;
    }

    calculateAccDeduction() {
        const accDeductionRate = 1.6;
        const accIncomeCap = 139384;
        return (Math.min(this.incomeAnnual, accIncomeCap) * accDeductionRate) / 100;
    }

    calculateKiwiSaverDeduction() {
        return this.kiwisaverChecked ? this.incomeAnnual * (this.kiwisaverValue / 100) : 0;
    }

    calculateStudentLoanDeduction() {
        const studentLoanRepaymentThreshold = 24128;
        return this.studentLoanChecked && this.incomeAnnual > studentLoanRepaymentThreshold
            ? (this.incomeAnnual - studentLoanRepaymentThreshold) * 0.12
            : 0;
    }

    calculateTakeHomePay() {
        const taxAmount = this.calculateIncomeTax();
        const kiwiSaverDeduction = this.calculateKiwiSaverDeduction();
        const studentLoanDeduction = this.calculateStudentLoanDeduction();
        const accDeduction = this.calculateAccDeduction();
        const takeHomePay = this.incomeAnnual - taxAmount - kiwiSaverDeduction - studentLoanDeduction - accDeduction;

        return {
            taxAmount,
            kiwiSaverDeduction,
            studentLoanDeduction,
            accDeduction,
            takeHomePay
        };
    }
}

class DisplayUpdater {
    static formatNumberWithCommas(number, decimalPlaces = 2) {
        return new Intl.NumberFormat('en-US', {
            style: 'decimal',
            minimumFractionDigits: decimalPlaces,
            maximumFractionDigits: decimalPlaces
        }).format(number);
    }

    static capitalizeFirstLetter(string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    }

    update(values, hoursValue) {
        const periods = {
            hour: 52 * hoursValue,
            week: 52,
            fortnight: 26,
            month: 12,
            year: 1
        };

        for (let period in periods) {
            const periodCapitalized = DisplayUpdater.capitalizeFirstLetter(period);
            document.getElementById(`grossPay${periodCapitalized}`).textContent = DisplayUpdater.formatNumberWithCommas(values.gross / periods[period]);
            document.getElementById(`payePer${periodCapitalized}`).textContent = DisplayUpdater.formatNumberWithCommas(values.tax / periods[period]);
            document.getElementById(`accPer${periodCapitalized}`).textContent = DisplayUpdater.formatNumberWithCommas(values.acc / periods[period]);
            document.getElementById(`kiwisaverPer${periodCapitalized}`).textContent = DisplayUpdater.formatNumberWithCommas(values.kiwisaver / periods[period]);
            document.getElementById(`studentLoanPer${periodCapitalized}`).textContent = DisplayUpdater.formatNumberWithCommas(values.studentLoan / periods[period]);
            document.getElementById(`takeHomePayPer${periodCapitalized}`).textContent = DisplayUpdater.formatNumberWithCommas(values.takeHome / periods[period]);
        }
    }
}

class ChartGenerator {
    constructor() {
        this.myPieChart = null;
    }

    generate(taxAmount, kiwiSaverDeduction, studentLoanDeduction, accDeduction, takeHomePay, taxcode, takeHomePayGross, takeHomePayWeek) {
        if (this.myPieChart) {
            this.myPieChart.destroy();
        }

        document.querySelector(".result-container").style.display = "flex";

        let ctx = document.getElementById('incomeBreakdownChart').getContext('2d');
        this.myPieChart = new Chart(ctx, {
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
}

class UIHandler {
    constructor() {
        this.initEventListeners();
    }

    initEventListeners() {
        document.getElementById('moreLink').addEventListener('click', this.toggleMoreOptions.bind(this));
        document.getElementById('hoursLink').addEventListener('click', this.toggleHoursOptions.bind(this));
        document.getElementById('kiwisaverLink').addEventListener('click', this.toggleKiwiSaverOptions.bind(this));
        document.getElementById('holidayPayLink').addEventListener('click', this.toggleHolidayPayOptions.bind(this));

        $(document).ready(() => {
            $('a[href^="#"]').on('click', function (event) {
                var target = $(this.getAttribute('href'));
                if (target.length) {
                    event.preventDefault();
                    $('html, body').stop().animate({
                        scrollTop: target.offset().top
                    }, 1000);
                }
            });
        });
    }

    toggleMoreOptions(e) {
        e.preventDefault();
        var moreOptions = document.getElementById('moreOptions');

        if (!moreOptions.classList.contains('visible')) {
            moreOptions.classList.add('visible');
        } else {
            moreOptions.classList.remove('visible');
            document.getElementById('hoursOptions').classList.remove('visible');
            document.getElementById('kiwisaverOptions').classList.remove('visible');
            document.getElementById('holidayPayOptions').classList.remove('visible');
        }
    }

    toggleHoursOptions(e) {
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
    }

    toggleKiwiSaverOptions(e) {
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
    }

    toggleHolidayPayOptions(e) {
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
    }
}

// Initialize UI Handler
const uiHandler = new UIHandler();

// Main Event Listener
document.getElementById("incomeForm").addEventListener("submit", function (event) {
    event.preventDefault();

    // Gather inputs
    var incomeValue = parseFloat(document.getElementById("incomeInput").value);
    var hoursValue = parseFloat(document.getElementById('hoursValue').value);
    const timePeriodSelected = document.getElementById('timePeriodSelect').value;
    const kiwisaverChecked = document.getElementById("kiwisaverCheckbox").checked;
    const studentLoanCheckbox = document.getElementById("studentLoanCheckbox").checked;
    const casualCheckbox = document.getElementById("casualCheckbox").checked;
    var kiwisaverValue = parseFloat(document.getElementById('kiwiSaverValue').value);
    var holidayPayValue = parseFloat(document.getElementById('holidayPayValue').value);

    // Validation and defaults
    if (isNaN(incomeValue) || incomeValue < 0) {
        $('#error').modal('show');
        return;
    }
    if (isNaN(hoursValue) || hoursValue <= 0) {
        hoursValue = 40;
    }
    if (isNaN(kiwisaverValue) || kiwisaverValue < 0) {
        kiwisaverValue = 0;
    }
    if (isNaN(holidayPayValue) || holidayPayValue < 0) {
        holidayPayValue = 0;
    }

    // Scroll to results
    $('#anchorLink').trigger('click');

    // Create IncomeCalculator instance
    const calculator = new IncomeCalculator({
        incomeValue: incomeValue,
        hoursValue: hoursValue,
        timePeriodSelected: timePeriodSelected,
        kiwisaverChecked: kiwisaverChecked,
        studentLoanChecked: studentLoanCheckbox,
        casualChecked: casualCheckbox,
        kiwisaverValue: kiwisaverValue,
        holidayPayValue: holidayPayValue
    });

    // Calculate annual income
    calculator.calculateAnnualIncome();

    // Calculate deductions and take-home pay
    const results = calculator.calculateTakeHomePay();

    // Update display
    const displayUpdater = new DisplayUpdater();
    displayUpdater.update({
        gross: calculator.incomeAnnual,
        tax: results.taxAmount,
        acc: results.accDeduction,
        kiwisaver: results.kiwiSaverDeduction,
        studentLoan: results.studentLoanDeduction,
        takeHome: results.takeHomePay
    }, hoursValue);

    // Update additional info
    let taxcode = studentLoanCheckbox ? "M SL" : "M";
    const takeHomePayGross = DisplayUpdater.formatNumberWithCommas((results.takeHomePay / calculator.incomeAnnual) * 100) + "%";
    const takeHomePayWeek = "$" + DisplayUpdater.formatNumberWithCommas(results.takeHomePay / 52);

    // Generate Chart
    const chartGenerator = new ChartGenerator();
    chartGenerator.generate(
        results.taxAmount,
        results.kiwiSaverDeduction,
        results.studentLoanDeduction,
        results.accDeduction,
        results.takeHomePay,
        taxcode,
        takeHomePayGross,
        takeHomePayWeek
    );
});
