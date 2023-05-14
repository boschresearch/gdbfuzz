module.exports = {
  purge: ['./src/*.js', './src/**/*.{js,jsx,ts,tsx}', './public/index.html'],
  darkMode: false, // or 'media' or 'class'
  theme: {
    fontFamily: { sans: ["Poppins"] },
    extend: {},
  },
  variants: {
    extend: {},
  },
  plugins: [],
}
