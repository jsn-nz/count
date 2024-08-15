# Count.co.nz - NZ PAYE Tax Calculator

Welcome to the repository for count.co.nz, a web application designed to calculate New Zealand's PAYE tax. The data for this calculator is sourced from [www.ird.govt.nz](https://www.ird.govt.nz).

## Features

- Accurate PAYE calculations based on NZ PAYE tax rates.
- Interactive charts to visualize tax breakdowns.
- Responsive design that works on both desktop and mobile devices.

## New Zealand Tax Brackets (As of July 31, 2024)

- $0 to $15,600: 10.5%
- $15,601 to $53,500: 17.5%
- $53,501 to $78,100: 30%
- $78,101 to $180,000: 33%
- Over $180,000: 39%
- Source: https://www.ird.govt.nz/pages/campaigns/personal-income-tax-threshold-changes

## PAYE Component Breakdown

- **ACC Levy**: Fixed at 1.46% of your income.
- **KiwiSaver**: Default rate is 3%, but adjustable.
- **Student Loan**: 12% repayment on income over $22,828.

## Technologies Used

- **Font**: [Hammersmith One](https://fonts.googleapis.com/css2?family=Hammersmith+One&display=swap) from Google Fonts
- **Frontend Framework**: [Bootstrap 4.5.2](https://getbootstrap.com/docs/4.5/getting-started/introduction/)
- **Chart Library**: [Chart.js](https://www.chartjs.org/)
- **JavaScript Libraries**:
  - [jQuery 3.5.1](https://jquery.com/)
  - [Popper.js 1.16.0](https://popper.js.org/)

## How to Use

1. Visit [count.co.nz](https://count.co.nz).
2. Enter your details and income.
3. View the calculated tax amount and the breakdown of the tax components.

## Acknowledgments

- Data sourced from [Inland Revenue Department New Zealand](https://www.ird.govt.nz).
- Bootstrap framework from [BootstrapCDN](https://maxcdn.bootstrapcdn.com/).
- Charting capabilities powered by [Chart.js](https://www.chartjs.org/).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

