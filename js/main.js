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

const 标点符号 = '，。！？；：、（）《》“”‘’——…—·「」『』〈〉〔〕【】〖〗〘〙〚〛～abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';

async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
    } catch {
    }
}

function annotate_pinyin(elements) {
    for (const p of elements) {
        const chars = p.textContent.split('');

        // Check if p has any images
        if (p.querySelector('img')) {
            continue;
        }

        p.addEventListener('click', function (text) {
            copyToClipboard(text);
        }.bind(p, p.textContent));


        p.dataset.text = p.textContent;
        p.textContent = '';


        for (const char of chars) {
            const ruby = document.createElement('ruby');
            const span = document.createElement('span');

            span.innerText = char;
            ruby.appendChild(span);

            if (!标点符号.includes(char)) {
                const pinyin = pinyinUtil.getPinyin(char, ' ', true, true);
                let rp = document.createElement('rp');
                rp.textContent = '(';
                ruby.appendChild(rp);
                const rt = document.createElement('rt');
                if (!'1234567890'.includes(char))
                    rt.textContent = pinyin;
                ruby.appendChild(rt);
                rp = document.createElement('rp');
                rp.textContent = ')';
                ruby.appendChild(rp);
            }

            p.appendChild(ruby);
        }
    }
}