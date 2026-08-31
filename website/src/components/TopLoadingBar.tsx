import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';

export default function TopLoadingBar() {
  const location = useLocation();
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];

    setProgress(0);
    setVisible(true);

    timers.current.push(setTimeout(() => setProgress(60), 60));
    timers.current.push(setTimeout(() => setProgress(85), 350));
    timers.current.push(setTimeout(() => setProgress(100), 650));
    timers.current.push(setTimeout(() => setVisible(false), 1000));

    return () => timers.current.forEach(clearTimeout);
  }, [location.pathname]);

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed top-0 left-0 right-0 z-[9999]"
      style={{ opacity: visible ? 1 : 0, transition: 'opacity 0.35s ease' }}
    >
      <div
        className="h-[3px] bg-gradient-to-r from-brand-400 via-brand-500 to-blue-500"
        style={{
          width: `${progress}%`,
          transition:
            progress === 0
              ? 'none'
              : progress === 100
              ? 'width 0.2s ease-out'
              : 'width 0.5s cubic-bezier(0.22, 1, 0.36, 1)',
        }}
      />
    </div>
  );
}
