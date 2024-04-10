document.addEventListener('DOMContentLoaded', function () {
    window.setInterval(function () {
        const h1 = document.querySelector('body>.container>header>h1');
        // The rotate value is like 'x 220deg'
        let rotate = h1.style.rotate;
        let angle = parseInt(rotate.split(' ')[1]);

        if (angle >= 360 || isNaN(angle)) {
            angle = 0;
        }

        angle += 1;
        h1.style.rotate = `x ${angle}deg`;
    }, 50)
});

const 标点符号 = '，。！？；：、（）《》“”‘’——…—·「」『』〈〉〔〕【】〖〗〘〙〚〛～1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';

function 标注拼音(elements) {
    for (const p of elements) {
        const chars = p.textContent.split('');

        // Check if p has any images
        if (p.querySelector('img')) {
            continue;
        }

        p.textContent = '';

        for (const c of chars) {
            const ruby = document.createElement('ruby');

            ruby.innerText = c;

            if (!标点符号.includes(c)) {
                const pinyin = pinyinUtil.getPinyin(c, ' ', true, true);

                ruby.textContent = c;

                let rp = document.createElement('rp');
                rp.textContent = '(';
                ruby.appendChild(rp);
                const rt = document.createElement('rt');
                rt.textContent = pinyin;
                ruby.appendChild(rt);
                rp = document.createElement('rp');
                rp.textContent = ')';
                ruby.appendChild(rp);

                // ruby.addEventListener('click', function () {

                // }.bind(pinyin));
            }

            p.appendChild(ruby);
        }
    }
}