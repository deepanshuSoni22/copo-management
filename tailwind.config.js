// tailwind.config.js
const defaultTheme = require('tailwindcss/defaultTheme'); // Import defaultTheme

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './copo_management_system/templates/**/*.html',
    './users/templates/**/*.html',
    './academics/templates/**/*.html',
    './**/templates/**/*.html',
  ],
  theme: {
    extend: {
      fontFamily: {
        poppins: ['Poppins', ...defaultTheme.fontFamily.sans],
      },
      // --- NEW COLOR DEFINITIONS ---
      colors: {
        'brand-purple': '#604993',    // For purple backgrounds, buttons
        'brand-yellow': '#FBB816',    // For highlighted texts, backgrounds
        'gray-default': '#767672',    // For general gray texts/elements
        'white-pure': '#FFFFFF',      // For white texts

        // You can also add shades if needed, e.g., for brand-purple
        // 'brand-purple-light': '#8F7ACC',
        // 'brand-purple-dark': '#403062',
      },
      // --- END NEW COLOR DEFINITIONS ---
    },
  },
  plugins: [],
}; // <-- ENSURE THIS SEMICOLON IS HERE