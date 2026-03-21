import { useState, useEffect, memo } from 'react';

const WMO = {
  0: 'CLEAR SKY', 1: 'MAINLY CLEAR', 2: 'PARTLY CLOUDY', 3: 'OVERCAST',
  45: 'FOGGY', 48: 'RIME FOG',
  51: 'LIGHT DRIZZLE', 61: 'LIGHT RAIN', 63: 'MODERATE RAIN', 65: 'HEAVY RAIN',
  71: 'LIGHT SNOW', 73: 'MODERATE SNOW', 75: 'HEAVY SNOW',
  80: 'SHOWERS', 95: 'THUNDERSTORM',
};

function fetchWeather(setWeather) {
  fetch(
    'https://api.open-meteo.com/v1/forecast?latitude=45.7983&longitude=24.1256' +
    '&current=temperature_2m,weather_code,precipitation_probability' +
    '&wind_speed_unit=kmh&timezone=Europe%2FBucharest'
  )
    .then(r => r.json())
    .then(d => setWeather({
      temp:   Math.round(d.current.temperature_2m),
      code:   d.current.weather_code,
      precip: d.current.precipitation_probability,
    }))
    .catch(() => {});
}

export default memo(function WeatherTimeWidget({ isOpacityFixed }) {
  const [time, setTime] = useState(new Date());
  const [weather, setWeather] = useState(null);

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    fetchWeather(setWeather);
    const interval = setInterval(() => fetchWeather(setWeather), 15 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`w-full h-full glass-panel rounded-2xl p-8 flex flex-col justify-center gap-10 border border-stark-cyan/20 bg-black/40 transition-opacity duration-500 ${isOpacityFixed ? 'opacity-100' : 'opacity-40 hover:opacity-100'}`}>
      <div className="text-stark-cyan font-mono">
        <h2 className="text-[10px] tracking-[0.3em] opacity-50 mb-4">LOCAL TIME // SIBIU</h2>
        <div className="text-6xl font-light tracking-wider drop-shadow-[0_0_8px_rgba(0,243,255,0.5)]">
          {time.toLocaleTimeString([], { hour12: false })}
        </div>
        <div className="text-sm tracking-widest opacity-70 mt-4">
          {time.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }).toUpperCase()}
        </div>
      </div>

      <div className="w-full h-[1px] bg-gradient-to-r from-stark-cyan/50 to-transparent" />

      <div className="text-stark-cyan font-mono">
        <h2 className="text-[10px] tracking-[0.3em] opacity-50 mb-4">ATMOSPHERICS</h2>
        <div className={`text-5xl font-light drop-shadow-[0_0_8px_rgba(0,243,255,0.5)] ${!weather ? 'animate-pulse' : ''}`}>
          {weather?.temp ?? '--'}°C
        </div>
        <div className={`text-xs tracking-widest opacity-70 mt-4 ${!weather ? 'animate-pulse' : ''}`}>
          {WMO[weather?.code] ?? 'LOADING...'}
        </div>
        {weather?.precip > 50 && (
          <div className="text-xs tracking-widest mt-2 text-stark-orange">
            WARNING: {weather.precip}% PRECIPITATION CHANCE
          </div>
        )}
      </div>
    </div>
  );
});
