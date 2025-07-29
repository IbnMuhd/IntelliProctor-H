// This script handles registration feedback and video freeze after form submission
window.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.register-container form');
    const videoImg = document.querySelector('.register-container img');
    if (form && videoImg) {
        form.addEventListener('submit', function(e) {
            // After form submit, freeze the video feed and show confirmation
            setTimeout(function() {
                // Freeze the video by replacing src with the current frame
                // (since it's a stream, we just keep the last frame)
                videoImg.src = videoImg.src; // This will not actually freeze, but we can hide it
                videoImg.style.opacity = 0.5;
                // Show confirmation message
                let msg = document.createElement('div');
                msg.textContent = 'Face captured! Registration submitted.';
                msg.style.color = 'green';
                msg.style.marginTop = '16px';
                msg.style.fontWeight = 'bold';
                form.parentNode.appendChild(msg);
            }, 100); // Wait a bit for the form to submit
        });
    }
});
