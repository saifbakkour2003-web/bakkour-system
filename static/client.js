// client.js
// تبادل التابات بين التقسيط والدين النقدي

document.addEventListener('DOMContentLoaded', () => {
    const tabs = document.querySelectorAll('.tab');
    const sections = document.querySelectorAll('.tab-content');

    tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.target;

            // إزالة active من كل التابات
            tabs.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // إخفاء كل الأقسام
            sections.forEach(sec => sec.style.display = 'none');

            // إظهار القسم المطلوب إذا موجود
            if(document.getElementById(target)){
                document.getElementById(target).style.display = 'block';
            }

        });
    });

    // افتراضياً افتح أول تاب
    if (tabs.length > 0) {
        tabs[0].click();
    }
});

