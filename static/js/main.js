/**
 * Aurevia Motors — Interactive Behaviors
 */

document.addEventListener('DOMContentLoaded', () => {
    // Smooth scrolling for in-page anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId.length > 1) {
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    e.preventDefault();
                    targetElement.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            }
        });
    });

    // Console branding message
    console.log(
        '%c AUREVIA MOTORS %c Luxury Supercar Atelier & Digital Showroom Initialized ',
        'background: #d4af37; color: #0a0c10; font-weight: bold; padding: 4px 8px; border-radius: 2px;',
        'background: #181d28; color: #f0f3f6; padding: 4px 8px;'
    );
});
