document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const speciesCards = document.querySelectorAll('.species-card');
    const ctx = document.getElementById('speciesChart').getContext('2d');

    // Theme Toggle
    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        themeToggle.textContent = document.body.classList.contains('dark-mode') ? '🌞' : '🌙';
    });

    // Species Chart
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            datasets: [
                {
                    label: 'Sparrow',
                    data: [12, 19, 3, 5, 2, 3],
                    borderColor: '#DAA520', // Darker gold color
                    backgroundColor: '#DAA520', // Added background color
                    borderWidth: 3,
                    tension: 0.1
                },
                {
                    label: 'Robin',
                    data: [2, 3, 20, 5, 1, 4],
                    borderColor: '#2E8B57', // Darker green color
                    backgroundColor: '#2E8B57', // Added background color
                    borderWidth: 3,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: document.body.classList.contains('dark-mode') ? '#e6b800' : '#ffd700'
                    }
                },
                x: {
                    ticks: {
                        color: document.body.classList.contains('dark-mode') ? '#e6b800' : '#ffd700'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: document.body.classList.contains('dark-mode') ? '#e6b800' : '#ffd700'
                    }
                }
            }
        }
    });

    // Species Card Click Handler
    speciesCards.forEach(card => {
        card.addEventListener('click', () => {
            const species = card.getAttribute('data-species');
            alert(`Detailed information for ${species}`);
        });
    });
});