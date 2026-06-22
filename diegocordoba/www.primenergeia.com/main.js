document.addEventListener("DOMContentLoaded", () => {
    // Scroll Reveal Animations
    const revealElements = document.querySelectorAll('.reveal');

    const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('active');
                observer.unobserve(entry.target); // Only animate once
            }
        });
    }, {
        root: null,
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px"
    });

    revealElements.forEach(el => revealObserver.observe(el));

    // Number Counter Animation
    const counters = document.querySelectorAll('.counter');
    const speed = 200; // The lower the slower

    const animateCounters = (counter) => {
        const updateCount = () => {
            const target = +counter.getAttribute('data-target');
            const count = +counter.innerText.replace(/,/g, '');
            const inc = target / speed;

            if (count < target) {
                counter.innerText = Math.ceil(count + inc).toLocaleString();
                setTimeout(updateCount, 10);
            } else {
                counter.innerText = target.toLocaleString();
            }
        };
        updateCount();
    };

    const counterObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounters(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.5
    });

    counters.forEach(counter => counterObserver.observe(counter));

    // Smooth Scrolling for Navbar Links
    document.querySelectorAll('.nav-links a').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if(targetId.startsWith('#')) {
                const targetElement = document.querySelector(targetId);
                if(targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            }
        });
    });

    // Parallax effect on ambient background
    document.addEventListener('mousemove', (e) => {
        const x = e.clientX / window.innerWidth;
        const y = e.clientY / window.innerHeight;
        
        const orbs = document.querySelectorAll('.glow-orb');
        orbs.forEach((orb, index) => {
            const factor = (index + 1) * 20;
            orb.style.transform = `translate(${x * factor}px, ${y * factor}px)`;
        });
    });

    // Telemetry Chart Setup - CONTINUOUS LIVE SIMULATION
    const ctx = document.getElementById('telemetryChart');
    if (ctx) {
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = "'Inter', sans-serif";

        // Create gradient fills
        let canvasCtx = ctx.getContext('2d');
        let gradientCyan = canvasCtx.createLinearGradient(0, 0, 0, 400);
        gradientCyan.addColorStop(0, 'rgba(0, 209, 255, 0.4)');
        gradientCyan.addColorStop(1, 'rgba(0, 209, 255, 0)');

        let gradientPurple = canvasCtx.createLinearGradient(0, 0, 0, 400);
        gradientPurple.addColorStop(0, 'rgba(157, 78, 221, 0.4)');
        gradientPurple.addColorStop(1, 'rgba(157, 78, 221, 0)');

        let telemetryChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(30).fill(''),
                datasets: [
                    {
                        label: 'Grid Stability (%)',
                        borderColor: '#00d1ff',
                        backgroundColor: gradientCyan,
                        borderWidth: 3,
                        pointRadius: 0,
                        tension: 0.4,
                        fill: true,
                        data: Array(30).fill(100),
                        yAxisID: 'y'
                    },
                    {
                        label: 'Granas PCE (%)',
                        borderColor: '#9d4edd',
                        backgroundColor: gradientPurple,
                        borderWidth: 2,
                        pointRadius: 0,
                        tension: 0.4,
                        fill: true,
                        data: Array(30).fill(33.5),
                        yAxisID: 'y'
                    },
                    {
                        label: 'H₂ Yield (kg/h)',
                        borderColor: '#10b981',
                        borderWidth: 3,
                        pointRadius: 0,
                        tension: 0.4,
                        fill: false,
                        data: Array(30).fill(25),
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 0 // Disable default animation for smooth scrolling
                },
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { display: false }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        min: 40,
                        max: 105
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        min: 0,
                        max: 40
                    }
                },
                plugins: {
                    legend: { position: 'top', labels: { usePointStyle: true, boxWidth: 8 } },
                    tooltip: {
                        backgroundColor: 'rgba(5,8,16,0.9)',
                        titleColor: '#fff',
                        bodyColor: '#e2e8f0',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1
                    }
                }
            }
        });

        // Continuous Data Generation
        let isDisturbed = false;
        let recoveryStep = 0;

        setInterval(() => {
            // Generate next data point
            let currentStability = telemetryChart.data.datasets[0].data[29];
            let nextStability = 100 + (Math.random() * 2 - 1); // Hover around 100
            let nextPCE = 33.5 + (Math.random() * 0.4 - 0.2); // Hover around 33.5
            let nextH2 = 25 + (Math.random() * 2 - 1); // Hover around 25

            if (isDisturbed) {
                if (recoveryStep === 0) {
                    // Initial severe drop
                    nextStability = 60 + Math.random() * 5;
                    nextPCE = 30 + Math.random() * 2;
                    nextH2 = 10 + Math.random() * 5;
                    recoveryStep++;
                } else if (recoveryStep < 10) {
                    // HJB Solver kicks in, rapid recovery
                    nextStability = currentStability + (100 - currentStability) * 0.4;
                    nextPCE = currentStability > 85 ? 33.5 : 31;
                    nextH2 = currentStability > 85 ? 25 : 15;
                    recoveryStep++;
                } else {
                    // Recovered
                    isDisturbed = false;
                    recoveryStep = 0;
                    document.getElementById('injectDisturbanceBtn').disabled = false;
                    document.getElementById('injectDisturbanceBtn').innerText = "⚡ Inject Disturbance";
                }
            }

            // Shift data arrays
            telemetryChart.data.datasets[0].data.shift();
            telemetryChart.data.datasets[0].data.push(nextStability);
            
            telemetryChart.data.datasets[1].data.shift();
            telemetryChart.data.datasets[1].data.push(nextPCE);
            
            telemetryChart.data.datasets[2].data.shift();
            telemetryChart.data.datasets[2].data.push(nextH2);

            telemetryChart.update();
        }, 800);

        // Disturbance Button
        const btn = document.getElementById('injectDisturbanceBtn');
        btn.addEventListener('click', () => {
            if (!isDisturbed) {
                isDisturbed = true;
                recoveryStep = 0;
                btn.disabled = true;
                btn.innerText = "HJB Solver Intervening...";
            }
        });
    }
});
