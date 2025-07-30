// startExam logic now handled inline in exam.html for better UX

// Periodic identity verification
setInterval(() => {
    fetch('/verify_identity', {method: 'POST'})
      .then(res => res.json())
      .then(data => {
        if (!data.verified) {
          alert('Identity verification failed!');
        }
      });
}, 5 * 60 * 1000);

// Screen activity monitoring (only for students)
if (typeof userRole === 'undefined' || userRole === 'student') {
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            fetch('/screen_activity', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({event: 'left_exam_screen'})
            });
            alert('You have left the exam screen!');
        }
    });
}