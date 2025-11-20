export function longpress(node: HTMLElement, params: { duration?: number, callback: () => void } | (() => void)) {
    let duration = 500;
    let callback: () => void;

    if (typeof params === 'function') {
        callback = params;
    } else {
        duration = params.duration ?? 500;
        callback = params.callback;
    }

    let timer: ReturnType<typeof setTimeout>;

    const handleMousedown = () => {
        timer = setTimeout(() => {
            callback();
        }, duration);
    };

    const handleMouseup = () => {
        clearTimeout(timer);
    };

    const handleTouchstart = (e: TouchEvent) => {
        timer = setTimeout(() => {
            callback();
        }, duration);
    };

    const handleTouchend = () => {
        clearTimeout(timer);
    };

    node.addEventListener('mousedown', handleMousedown);
    node.addEventListener('mouseup', handleMouseup);
    node.addEventListener('mouseleave', handleMouseup);
    node.addEventListener('touchstart', handleTouchstart);
    node.addEventListener('touchend', handleTouchend);
    node.addEventListener('touchcancel', handleTouchend);

    return {
        update(newParams: { duration?: number, callback: () => void } | (() => void)) {
            if (typeof newParams === 'function') {
                callback = newParams;
            } else {
                duration = newParams.duration ?? 500;
                callback = newParams.callback;
            }
        },
        destroy() {
            node.removeEventListener('mousedown', handleMousedown);
            node.removeEventListener('mouseup', handleMouseup);
            node.removeEventListener('mouseleave', handleMouseup);
            node.removeEventListener('touchstart', handleTouchstart);
            node.removeEventListener('touchend', handleTouchend);
            node.removeEventListener('touchcancel', handleTouchend);
        }
    };
}
