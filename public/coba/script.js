// script.js
document.addEventListener('DOMContentLoaded', function () {
  const chatBtn = document.getElementById('chatBtn');
  const chatBubble = document.getElementById('chatBubble');
  const closeBtn = document.getElementById('closeBtn');

  chatBtn.addEventListener('click', function () {
    chatBubble.style.display = 'flex';
    chatBtn.style.display = 'none';
  });

  closeBtn.addEventListener('click', function () {
    chatBubble.style.display = 'none';
    chatBtn.style.display = 'block';
  });
});
