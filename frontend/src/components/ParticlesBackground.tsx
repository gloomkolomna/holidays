import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

const COLORS = ['#e0a83e', '#f4d58d', '#c2185b', '#ffffff', '#6b3fa0'];

interface Particle {
  x: number;
  y: number;
  size: number;
  speed: number;
  sway: number;
  phase: number;
  color: string;
  rotation: number;
  rotSpeed: number;
  vx: number;
  vy: number;
}

export default function ParticlesBackground({
  preset,
  imageUrl,
  size = 50,
  count,
  opacity = 100,
}: {
  preset?: string;
  imageUrl?: string | null;
  size?: number;
  count?: number;
  opacity?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const spriteMode = !!imageUrl;
  const active = spriteMode || (!!preset && preset !== 'none');

  useEffect(() => {
    if (!active) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let width = window.innerWidth;
    let height = window.innerHeight;

    const resize = () => {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    window.addEventListener('resize', resize);

    let img: HTMLImageElement | null = null;
    let aspect = 1;
    let imgReady = false;
    if (spriteMode && imageUrl) {
      img = new Image();
      img.onload = () => {
        if (img && img.naturalWidth > 0) {
          aspect = img.naturalHeight / img.naturalWidth;
          imgReady = true;
        }
      };
      img.src = imageUrl;
    }

    const baseSize = 16 + (size / 100) * 88;
    const num = count ?? Math.min(28, Math.max(10, Math.floor(width / 30)));
    const baseAlpha = Math.min(1, Math.max(0.1, opacity / 100));
    const speedMin = preset === 'snow' ? 8 : preset === 'sparkles' ? 4 : 14;
    const speedMax = preset === 'snow' ? 18 : preset === 'sparkles' ? 10 : 40;
    const particles: Particle[] = Array.from({ length: num }, () => {
      const angle = Math.random() * Math.PI * 2;
      const speed = 20 + Math.random() * 35;
      return {
        x: Math.random() * width,
        y: Math.random() * height,
        size: baseSize * (0.7 + Math.random() * 0.6),
        speed: speedMin + Math.random() * (speedMax - speedMin),
        sway: 14 + Math.random() * 26,
        phase: Math.random() * Math.PI * 2,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        rotation: Math.random() * Math.PI,
        rotSpeed: (Math.random() - 0.5) * 2,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
      };
    });

    let raf = 0;
    let last = performance.now();

    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      ctx.clearRect(0, 0, width, height);

      const drawSprite = imgReady && img;
      for (const p of particles) {
        if (drawSprite) {
          const steer = 60;
          p.vx += (Math.random() - 0.5) * steer * dt;
          p.vy += (Math.random() - 0.5) * steer * dt;
          const v = Math.hypot(p.vx, p.vy) || 1;
          const minV = 14;
          const maxV = 70;
          if (v < minV) {
            p.vx = (p.vx / v) * minV;
            p.vy = (p.vy / v) * minV;
          } else if (v > maxV) {
            p.vx = (p.vx / v) * maxV;
            p.vy = (p.vy / v) * maxV;
          }
          p.x += p.vx * dt;
          p.y += p.vy * dt;
          p.phase += dt;
          const m = p.size;
          if (p.x < m / 2) { p.x = m / 2; p.vx = Math.abs(p.vx); }
          if (p.x > width - m / 2) { p.x = width - m / 2; p.vx = -Math.abs(p.vx); }
          if (p.y < m / 2) { p.y = m / 2; p.vy = Math.abs(p.vy); }
          if (p.y > height - m / 2) { p.y = height - m / 2; p.vy = -Math.abs(p.vy); }
        } else {
          p.y += p.speed * dt;
          p.phase += dt;
          p.rotation += p.rotSpeed * dt;
          if (p.y > height + p.size) {
            p.y = -p.size;
            p.x = Math.random() * width;
          }
        }
        const x = drawSprite ? p.x : p.x + Math.sin(p.phase) * p.sway * 0.3;

        if (drawSprite) {
          const w = p.size;
          const h = p.size * aspect;
          ctx.save();
          ctx.translate(x, p.y);
          ctx.rotate(Math.sin(p.phase) * 0.12);
          ctx.globalAlpha = 0.9 * baseAlpha;
          ctx.drawImage(img!, -w / 2, -h / 2, w, h);
          ctx.restore();
        } else {
          ctx.save();
          ctx.translate(x, p.y);
          if (preset === 'snow') {
            ctx.globalAlpha = 0.85 * baseAlpha;
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
            ctx.fill();
          } else if (preset === 'sparkles') {
            const twinkle = Math.abs(Math.sin(p.phase * 2));
            const s = (p.size / 2) * (0.4 + twinkle * 0.8);
            ctx.globalAlpha = (0.3 + twinkle * 0.7) * baseAlpha;
            ctx.strokeStyle = '#ffe9a8';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(-s, 0); ctx.lineTo(s, 0);
            ctx.moveTo(0, -s); ctx.lineTo(0, s);
            ctx.stroke();
          } else {
            ctx.rotate(p.rotation);
            ctx.fillStyle = p.color;
            ctx.globalAlpha = 0.75 * baseAlpha;
            ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
          }
          ctx.restore();
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, [active, spriteMode, imageUrl, size, count, opacity, preset]);

  if (!active) return null;

  return createPortal(
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 5,
        pointerEvents: 'none',
      }}
    />,
    document.body,
  );
}
