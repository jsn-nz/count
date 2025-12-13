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
        initialHourlyRate = undefined;

        let incomeValue = this.incomeValue;
        let hoursValue = this.hoursValue;

        switch (this.timePeriodSelected) {
            case "Hour":
                incomeValue *= hoursValue * 52;
                break;
            case "Week":
                incomeValue *= 52;
                break;
            case "Fortnight":
                incomeValue *= 26;
                break;
            case "Month":
                incomeValue *= 12;
                break;
            case "Year":
                if (typeof initialHourlyRate === "undefined") {
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
            tax = 15600 * 0.105 + (53500 - 15600) * 0.175 + (income - 53500) * 0.3;
        } else if (income <= 180000) {
            tax =
                15600 * 0.105 +
                (53500 - 15600) * 0.175 +
                (78100 - 53500) * 0.3 +
                (income - 78100) * 0.33;
        } else {
            tax =
                15600 * 0.105 +
                (53500 - 15600) * 0.175 +
                (78100 - 53500) * 0.3 +
                (180000 - 78100) * 0.33 +
                (income - 180000) * 0.39;
        }

        return tax;
    }

    calculateAccDeduction() {
        const accDeductionRate = 1.45;
        const accIncomeCap = 152790;
        return (Math.min(this.incomeAnnual, accIncomeCap) * accDeductionRate) / 100;
    }

    calculateKiwiSaverDeduction() {
        return this.kiwisaverChecked
            ? this.incomeAnnual * (this.kiwisaverValue / 100)
            : 0;
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
        const takeHomePay =
            this.incomeAnnual -
            taxAmount -
            kiwiSaverDeduction -
            studentLoanDeduction -
            accDeduction;

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
        return new Intl.NumberFormat("en-US", {
            style: "decimal",
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
            document.getElementById(
                `grossPay${periodCapitalized}`
            ).textContent = DisplayUpdater.formatNumberWithCommas(
                values.gross / periods[period]
            );
            document.getElementById(
                `payePer${periodCapitalized}`
            ).textContent = DisplayUpdater.formatNumberWithCommas(
                values.tax / periods[period]
            );
            document.getElementById(
                `accPer${periodCapitalized}`
            ).textContent = DisplayUpdater.formatNumberWithCommas(
                values.acc / periods[period]
            );
            document.getElementById(
                `kiwisaverPer${periodCapitalized}`
            ).textContent = DisplayUpdater.formatNumberWithCommas(
                values.kiwisaver / periods[period]
            );
            document.getElementById(
                `studentLoanPer${periodCapitalized}`
            ).textContent = DisplayUpdater.formatNumberWithCommas(
                values.studentLoan / periods[period]
            );
            document.getElementById(
                `takeHomePayPer${periodCapitalized}`
            ).textContent = DisplayUpdater.formatNumberWithCommas(
                values.takeHome / periods[period]
            );
        }
    }
}

class ChartGenerator {
    constructor() {
        this.myPieChart = null;
    }

    generate(
        taxAmount,
        kiwiSaverDeduction,
        studentLoanDeduction,
        accDeduction,
        takeHomePay,
        taxcode,
        takeHomePayGross,
        takeHomePayWeek
    ) {
        if (this.myPieChart) {
            this.myPieChart.destroy();
        }

        document.querySelector(".result-container").style.display = "flex";

        const ctx = document
            .getElementById("incomeBreakdownChart")
            .getContext("2d");

        this.myPieChart = new Chart(ctx, {
            type: "pie",
            data: {
                labels: [
                    "PAYE",
                    "Kiwisaver",
                    "Student Loan",
                    "ACC",
                    "Take Home Pay"
                ],
                datasets: [
                    {
                        data: [
                            taxAmount,
                            kiwiSaverDeduction,
                            studentLoanDeduction,
                            accDeduction,
                            takeHomePay
                        ],
                        backgroundColor: [
                            "#ff5733",
                            "#f9c74f",
                            "#90be6d",
                            "#f8961e",
                            "#577590"
                        ]
                    }
                ]
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
        document
            .getElementById("moreLink")
            .addEventListener("click", this.toggleMoreOptions.bind(this));
        document
            .getElementById("hoursLink")
            .addEventListener("click", this.toggleHoursOptions.bind(this));
        document
            .getElementById("kiwisaverLink")
            .addEventListener("click", this.toggleKiwiSaverOptions.bind(this));
        document
            .getElementById("holidayPayLink")
            .addEventListener("click", this.toggleHolidayPayOptions.bind(this));

        document
            .getElementById("timePeriodSelect")
            .addEventListener("change", this.handleTimePeriodChange.bind(this));

        $(document).ready(() => {
            $('a[href^="#"]').on("click", function (event) {
                const target = $(this.getAttribute("href"));
                if (target.length) {
                    event.preventDefault();
                    $("html, body")
                        .stop()
                        .animate(
                            {
                                scrollTop: target.offset().top
                            },
                            1000
                        );
                }
            });
        });
    }

    handleTimePeriodChange(event) {
        const selectedValue = event.target.value;
        const moreOptions = document.getElementById("moreOptions");
        const hoursOptions = document.getElementById("hoursOptions");
        const kiwisaverOptions = document.getElementById("kiwisaverOptions");
        const holidayPayOptions = document.getElementById("holidayPayOptions");

        if (selectedValue === "Hour") {
            moreOptions.classList.add("visible");
            this.showElement(hoursOptions);
            this.hideElementInstantly(kiwisaverOptions);
            this.hideElementInstantly(holidayPayOptions);
        } else {
            this.hideElementInstantly(hoursOptions);

            if (
                !kiwisaverOptions.classList.contains("visible") &&
                !holidayPayOptions.classList.contains("visible")
            ) {
                moreOptions.classList.remove("visible");
            }
        }
    }

    toggleMoreOptions(e) {
        e.preventDefault();
        const moreOptions = document.getElementById("moreOptions");
        moreOptions.classList.toggle("visible");

        if (!moreOptions.classList.contains("visible")) {
            this.hideAllSubOptionsInstantly();
        }
    }

    hideAllSubOptionsInstantly() {
        const subOptions = ["hoursOptions", "kiwisaverOptions", "holidayPayOptions"];
        subOptions.forEach(id => {
            const element = document.getElementById(id);
            this.hideElementInstantly(element);
        });
    }

    toggleHoursOptions(e) {
        e.preventDefault();
        this.toggleOption("hoursOptions");
    }

    toggleKiwiSaverOptions(e) {
        e.preventDefault();
        this.toggleOption("kiwisaverOptions");
    }

    toggleHolidayPayOptions(e) {
        e.preventDefault();
        this.toggleOption("holidayPayOptions");
    }

    toggleOption(id) {
        const element = document.getElementById(id);
        const isCurrentlyVisible = element.classList.contains("visible");

        this.hideAllSubOptionsInstantly();

        if (!isCurrentlyVisible) {
            this.showElement(element);
        }
    }

    showElement(element) {
        element.classList.remove("instant-hide");
        void element.offsetWidth;
        element.classList.add("visible");
    }

    hideElementInstantly(element) {
        element.classList.add("instant-hide");
        element.classList.remove("visible");
    }
}

const uiHandler = new UIHandler();
const chartGenerator = new ChartGenerator();

document.getElementById("incomeForm").addEventListener("submit", function (event) {
    event.preventDefault();

    let incomeValue = parseFloat(document.getElementById("incomeInput").value);
    let hoursValue = parseFloat(document.getElementById("hoursValue").value);
    const timePeriodSelected = document.getElementById("timePeriodSelect").value;
    const kiwisaverChecked = document.getElementById("kiwisaverCheckbox").checked;
    const studentLoanCheckbox = document.getElementById("studentLoanCheckbox").checked;
    const casualCheckbox = document.getElementById("casualCheckbox").checked;
    let kiwisaverValue = parseFloat(document.getElementById("kiwiSaverValue").value);
    let holidayPayValue = parseFloat(document.getElementById("holidayPayValue").value);

    if (isNaN(incomeValue) || incomeValue < 0) {
        $("#error").modal("show");
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

    $("html, body").animate(
        {
            scrollTop: $("#table-div").offset().top
        },
        1000
    );

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

    calculator.calculateAnnualIncome();

    const results = calculator.calculateTakeHomePay();

    const displayUpdater = new DisplayUpdater();
    displayUpdater.update(
        {
            gross: calculator.incomeAnnual,
            tax: results.taxAmount,
            acc: results.accDeduction,
            kiwisaver: results.kiwiSaverDeduction,
            studentLoan: results.studentLoanDeduction,
            takeHome: results.takeHomePay
        },
        hoursValue
    );

    const taxcode = studentLoanCheckbox ? "M SL" : "M";
    const takeHomePayGross =
        DisplayUpdater.formatNumberWithCommas(
            (results.takeHomePay / calculator.incomeAnnual) * 100
        ) + "%";
    const takeHomePayWeek =
        "$" + DisplayUpdater.formatNumberWithCommas(results.takeHomePay / 52);

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
