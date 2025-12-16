import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  ShoppingCart,
  Menu,
  X,
  Instagram,
  Facebook,
  Twitter,
  Mail,
} from "lucide-react";
import { motion } from "framer-motion";
import heroModel from "../../assets/model.png";

const LandingPage = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-orange-50 via-yellow-50 to-red-50 overflow-x-hidden scroll-smooth">
      {/* NAVBAR */}
      <motion.nav
        initial={{ y: -100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="fixed top-0 left-0 right-0 w-full z-50 bg-gradient-to-r from-red-600 to-orange-600 backdrop-blur-sm shadow-sm"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            {/* Left - Logo and Navigation */}
            <div className="flex items-center space-x-8 lg:space-x-12">
              {/* Logo */}
              <a href="/" className="flex flex-col items-center flex-shrink-0">
                <div className="w-10 h-10 sm:w-12 sm:h-12 border-2 border-yellow-300 flex items-center justify-center mb-1">
                  <div
                    className="w-5 h-5 sm:w-6 sm:h-6 border border-yellow-300"
                    style={{
                      clipPath: "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)",
                    }}
                  ></div>
                </div>
                <span className="text-xs sm:text-sm font-semibold tracking-widest text-yellow-100">
                  EDGE
                </span>
              </a>

              {/* Desktop Navigation */}
              <div className="hidden lg:flex items-center space-x-8">
                <a
                  href="#home"
                  className="text-xs font-medium text-yellow-100 hover:text-yellow-200 transition-colors tracking-wider border-b-2 border-yellow-300 pb-1"
                >
                  HOME
                </a>
                <a
                  href="#categories"
                  className="text-xs font-medium text-yellow-100 hover:text-yellow-200 transition-colors tracking-wider"
                >
                  FEATURES
                </a>
                <a
                  href="#products"
                  className="text-xs font-medium text-yellow-100 hover:text-yellow-200 transition-colors tracking-wider"
                >
                  PRODUCTS
                </a>
                <a
                  href="#contact"
                  className="text-xs font-medium text-yellow-100 hover:text-yellow-200 transition-colors tracking-wider"
                >
                  CONTACT
                </a>
              </div>
            </div>

            {/* Right - Sign In and Cart */}
            <div className="hidden md:flex items-center space-x-6">
              <button className="text-xs font-medium text-yellow-100 hover:text-yellow-200 transition-colors tracking-wider">
                SIGN IN
              </button>
              <button className="relative p-2 text-yellow-100 hover:text-yellow-200 transition-colors">
                <ShoppingCart className="w-5 h-5" />
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-yellow-400 text-red-700 text-xs rounded-full flex items-center justify-center">
                  0
                </span>
              </button>
            </div>

            {/* Mobile Menu Button */}
            <div className="lg:hidden">
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="p-2 text-yellow-100"
              >
                {mobileMenuOpen ? (
                  <X className="w-6 h-6" />
                ) : (
                  <Menu className="w-6 h-6" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="lg:hidden border-t border-red-400 bg-gradient-to-r from-red-600 to-orange-600"
          >
            <div className="px-6 py-6 space-y-4 max-w-7xl mx-auto">
              <motion.a
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.1 }}
                href="#home"
                className="block text-sm font-medium text-yellow-100 hover:text-yellow-200 transition-colors"
              >
                HOME
              </motion.a>
              <motion.a
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.15 }}
                href="#categories"
                className="block text-sm font-medium text-yellow-100 hover:text-yellow-200 transition-colors"
              >
                FEATURES
              </motion.a>
              <motion.a
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.2 }}
                href="#products"
                className="block text-sm font-medium text-yellow-100 hover:text-yellow-200 transition-colors"
              >
                PRODUCTS
              </motion.a>
              <motion.a
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.25 }}
                href="#contact"
                className="block text-sm font-medium text-yellow-100 hover:text-yellow-200 transition-colors"
              >
                CONTACT
              </motion.a>
              <motion.div
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="pt-4 border-t border-red-400"
              >
                <button className="text-sm font-medium text-yellow-100 hover:text-yellow-200 transition-colors">
                  SIGN IN
                </button>
              </motion.div>
            </div>
          </motion.div>
        )}
      </motion.nav>

      {/* HERO SECTION */}
      <section
        id="home"
        className="relative min-h-[calc(100vh-5rem)] w-full overflow-hidden pt-20"
      >
        {/* Fullscreen Hero Image */}
        <motion.img
          src={heroModel}
          alt="Fashion model"
          initial={{ scale: 1.1, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          className="absolute inset-0 w-full h-full object-cover object-left-top pointer-events-none"
        />

        {/* Color Overlay */}
        <div className="absolute inset-0 bg-gradient-to-r from-red-900/30 via-orange-500/40 to-yellow-400/70" />

        {/* Content */}
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full min-h-[calc(100vh-5rem)] flex items-center">
          <div className="w-full flex justify-end py-12 lg:py-0">
            {/* Right side - Content */}
            <div className="relative z-10 space-y-6 lg:space-y-8 max-w-xl text-left">
              {/* Decorative wavy line */}
              <motion.div
                initial={{ opacity: 0, x: -50 }}
                animate={{ opacity: 0.8, x: 0 }}
                transition={{ duration: 0.8, delay: 0.3 }}
              >
                <svg
                  className="w-40 sm:w-56 h-10 sm:h-14 opacity-80"
                  viewBox="0 0 250 60"
                  preserveAspectRatio="none"
                >
                  <path
                    d="M 0 30 Q 60 10, 120 30 T 240 30"
                    stroke="#991b1b"
                    strokeWidth="1.5"
                    fill="none"
                  />
                </svg>
              </motion.div>

              {/* Main Heading */}
              <div className="space-y-4">
                <motion.h1
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: 0.4 }}
                  className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black tracking-tighter text-red-800 leading-[0.9] uppercase"
                >
                  Timeless
                  <br />
                  Fashion
                </motion.h1>
                <motion.span
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: 0.6 }}
                  className="block text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-black text-red-800 uppercase"
                >
                  For The Modern Era
                </motion.span>
              </div>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.8 }}
                className="text-sm sm:text-base text-red-900 leading-relaxed font-normal tracking-wide max-w-md"
              >
                We sell exclusive, sophisticated, and contemporary outfits for
                men and women.
              </motion.p>

              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.6, delay: 1.0 }}
                className="pt-2 flex flex-col sm:flex-row gap-3 sm:gap-4"
              >
                <Link to="/kiosk">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="group relative px-8 sm:px-10 py-3 sm:py-4 border-2 border-red-800 bg-red-700 text-white font-medium hover:bg-white hover:text-red-800 transition-all duration-300 tracking-widest text-xs sm:text-sm uppercase overflow-hidden shadow-lg"
                  >
                    <span className="relative z-10"> Kiosk Chat</span>
                  </motion.button>
                </Link>
                <Link to="/chat">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="group relative px-8 sm:px-10 py-3 sm:py-4 border-2 border-red-800 bg-white text-red-800 font-medium hover:bg-red-700 hover:text-white transition-all duration-300 tracking-widest text-xs sm:text-sm uppercase overflow-hidden shadow-lg"
                  >
                    <span className="relative z-10"> WhatsApp Chat</span>
                  </motion.button>
                </Link>
              </motion.div>

              {/* Social Links */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 1.2 }}
                className="pt-4 flex items-center space-x-3 sm:space-x-4"
              >
                {[Instagram, Facebook, Twitter, Mail].map((Icon, index) => (
                  <motion.a
                    key={index}
                    href="#"
                    initial={{ opacity: 0, scale: 0 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.4, delay: 1.2 + index * 0.1 }}
                    whileHover={{ scale: 1.1, rotate: 5 }}
                    whileTap={{ scale: 0.9 }}
                    className="w-8 h-8 sm:w-10 sm:h-10 rounded-full border-2 border-red-700 bg-yellow-50/90 backdrop-blur-sm flex items-center justify-center hover:bg-red-700 hover:text-white transition-all duration-300"
                  >
                    <Icon className="w-4 h-4" />
                  </motion.a>
                ))}
              </motion.div>

              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 1.6 }}
                className="text-xs tracking-widest font-mono text-red-900"
              >
                WWW.EDGELIFESTYLE.COM
              </motion.p>
            </div>
          </div>
        </div>
      </section>

      {/* FEATURE HIGHLIGHTS */}
      <section
        id="categories"
        className="py-16 sm:py-20 lg:py-24 w-full bg-gradient-to-br from-yellow-50 to-orange-50"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-2xl mx-auto mb-12 sm:mb-16"
          >
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              Why Choose EDGE
            </h2>
            <p className="text-base sm:text-lg text-gray-600">
              Experience fashion that speaks to your individuality
            </p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 lg:gap-8">
            {[
              {
                title: "Premium Quality",
                desc: "Meticulously crafted from the finest materials for unparalleled luxury and comfort.",
              },
              {
                title: "Timeless Design",
                desc: "Classic pieces that transcend trends, designed to remain stylish season after season.",
              },
              {
                title: "Sustainable Fashion",
                desc: "Ethically sourced and produced with minimal environmental impact for conscious consumers.",
              },
              {
                title: "Expert Tailoring",
                desc: "Perfect fit guaranteed with complimentary alterations by master craftspeople.",
              },
            ].map((feature, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
                whileHover={{ y: -10 }}
                className="group cursor-pointer"
              >
                <div className="relative h-64 sm:h-72 lg:h-80 bg-gradient-to-br from-red-200 to-orange-200 rounded-lg overflow-hidden mb-4 sm:mb-6 shadow-lg">
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    transition={{ duration: 0.5 }}
                    className="absolute inset-0 bg-gradient-to-br from-red-300 to-yellow-400 flex items-center justify-center"
                  >
                    <p className="text-red-900 text-sm">
                      Feature Image {idx + 1}
                    </p>
                  </motion.div>
                </div>
                <h3 className="text-lg sm:text-xl font-semibold text-gray-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm sm:text-base text-gray-600">
                  {feature.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* PROMO BANNER */}
      <section className="py-16 sm:py-20 lg:py-24 w-full bg-gradient-to-r from-red-700 via-red-600 to-orange-600 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-4xl mx-auto"
          >
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-4 sm:mb-6">
              Spring Collection 2025
            </h2>
            <p className="text-lg sm:text-xl text-yellow-100 mb-3 sm:mb-4">
              SALE WEEKEND • MAY 12-14
            </p>
            <p className="text-base sm:text-lg text-yellow-50 mb-8 sm:mb-10 max-w-2xl mx-auto">
              Get up to 40% off on selected items from our latest collection.
              Limited time offer. Premium fashion at unbeatable prices.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/kiosk">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="px-6 sm:px-8 py-3 sm:py-4 bg-yellow-400 text-red-900 text-sm sm:text-base font-medium hover:bg-yellow-300 transition-colors"
                >
                  SHOP WITH KIOSK
                </motion.button>
              </Link>
              <Link to="/chat">
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="px-6 sm:px-8 py-3 sm:py-4 border-2 border-yellow-400 text-yellow-100 text-sm sm:text-base font-medium hover:bg-yellow-400 hover:text-red-900 transition-colors"
                >
                  CHAT WITH US
                </motion.button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* PRODUCTS PREVIEW */}
      <section
        id="products"
        className="py-16 sm:py-20 lg:py-24 w-full bg-gradient-to-br from-orange-50 to-yellow-50"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.6 }}
            className="text-center max-w-2xl mx-auto mb-12 sm:mb-16"
          >
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-gray-900 mb-4">
              Featured Products
            </h2>
            <p className="text-base sm:text-lg text-gray-600">
              Handpicked selections from our latest arrivals
            </p>
          </motion.div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
            {[1, 2, 3, 4, 5, 6].map((item) => (
              <motion.div
                key={item}
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.5, delay: (item - 1) * 0.1 }}
                whileHover={{ y: -5, scale: 1.02 }}
                className="group cursor-pointer bg-white rounded-lg overflow-hidden shadow-lg hover:shadow-xl transition-shadow"
              >
                <div className="relative h-72 sm:h-80 lg:h-96 bg-gradient-to-br from-red-200 to-orange-200 overflow-hidden">
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    transition={{ duration: 0.5 }}
                    className="absolute inset-0 bg-gradient-to-br from-red-300 to-yellow-400 flex items-center justify-center"
                  >
                    <p className="text-red-900 text-sm">Product Image {item}</p>
                  </motion.div>
                </div>
                <div className="p-4 sm:p-6">
                  <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-2">
                    Premium Product Name
                  </h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Brief product description goes here
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-lg sm:text-xl font-bold text-gray-900">
                      $299
                    </span>
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      className="px-3 sm:px-4 py-2 bg-red-700 text-white text-xs sm:text-sm font-medium hover:bg-red-800 transition-colors"
                    >
                      ADD TO CART
                    </motion.button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="text-center mt-10 sm:mt-12">
            <Link to="/kiosk">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-6 sm:px-8 py-3 sm:py-4 border-2 border-red-700 text-red-800 text-sm sm:text-base font-medium hover:bg-red-700 hover:text-white transition-colors"
              >
                VIEW ALL PRODUCTS
              </motion.button>
            </Link>
          </div>
        </div>
      </section>

      {/* NEWSLETTER */}
      <section className="py-16 sm:py-20 lg:py-24 w-full bg-gradient-to-br from-yellow-50 to-orange-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.6 }}
            className="text-center"
          >
            <h2 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-4">
              Stay Updated
            </h2>
            <p className="text-base sm:text-lg text-gray-600 mb-8">
              Subscribe to receive exclusive offers and style insights
            </p>
            <form className="flex flex-col sm:flex-row gap-4 max-w-xl mx-auto">
              <input
                type="email"
                placeholder="Enter your email address"
                className="flex-1 px-4 sm:px-6 py-3 sm:py-4 border-2 border-red-300 focus:border-red-700 focus:outline-none text-sm sm:text-base"
              />
              <motion.button
                type="submit"
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="px-6 sm:px-8 py-3 sm:py-4 bg-red-700 text-white text-sm sm:text-base font-medium hover:bg-red-800 transition-colors whitespace-nowrap"
              >
                SUBSCRIBE
              </motion.button>
            </form>
          </motion.div>
        </div>
      </section>

      {/* FOOTER */}
      <footer
        id="contact"
        className="w-full bg-gradient-to-br from-red-900 via-red-800 to-orange-800 text-white pt-12 sm:pt-16 pb-6 sm:pb-8"
      >
        <motion.div
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, amount: 0.1 }}
          transition={{ duration: 0.8 }}
          className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-12 mb-8 sm:mb-12">
            {/* Company Info */}
            <div>
              <h3 className="text-xl sm:text-2xl font-bold mb-4">EDGE</h3>
              <p className="text-sm sm:text-base text-yellow-100 mb-6">
                Redefining premium fashion with timeless elegance and
                contemporary design.
              </p>
              <div className="flex space-x-4">
                <a
                  href="#"
                  className="text-yellow-200 hover:text-white transition-colors"
                >
                  <Instagram className="w-5 h-5" />
                </a>
                <a
                  href="#"
                  className="text-yellow-200 hover:text-white transition-colors"
                >
                  <Facebook className="w-5 h-5" />
                </a>
                <a
                  href="#"
                  className="text-yellow-200 hover:text-white transition-colors"
                >
                  <Twitter className="w-5 h-5" />
                </a>
                <a
                  href="#"
                  className="text-yellow-200 hover:text-white transition-colors"
                >
                  <Mail className="w-5 h-5" />
                </a>
              </div>
            </div>

            {/* Quick Links */}
            <div>
              <h4 className="text-base sm:text-lg font-semibold mb-4">
                Quick Links
              </h4>
              <ul className="space-y-2 text-sm sm:text-base">
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    About Us
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    Our Story
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    Careers
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    Press
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    Blog
                  </a>
                </li>
              </ul>
            </div>

            {/* Customer Service */}
            <div>
              <h4 className="text-base sm:text-lg font-semibold mb-4">
                Customer Service
              </h4>
              <ul className="space-y-2 text-sm sm:text-base">
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    Contact Us
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    Shipping Info
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    Returns & Exchanges
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    Size Guide
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    FAQs
                  </a>
                </li>
              </ul>
            </div>

            {/* Legal */}
            <div>
              <h4 className="text-base sm:text-lg font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm sm:text-base">
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    Privacy Policy
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    Terms of Service
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    Cookie Policy
                  </a>
                </li>
                <li>
                  <a
                    href="#"
                    className="text-yellow-100 hover:text-white transition-colors"
                  >
                    Accessibility
                  </a>
                </li>
              </ul>
            </div>
          </div>

          {/* Bottom Bar */}
          <div className="pt-6 sm:pt-8 border-t border-red-700">
            <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
              <p className="text-yellow-100 text-sm sm:text-base">
                &copy; 2024 EDGE Lifestyle. All rights reserved.
              </p>
              <div className="flex space-x-6">
                <a
                  href="#"
                  className="text-yellow-100 hover:text-white transition-colors text-sm sm:text-base"
                >
                  Privacy Policy
                </a>
                <a
                  href="#"
                  className="text-yellow-100 hover:text-white transition-colors text-sm sm:text-base"
                >
                  Terms of Service
                </a>
              </div>
            </div>
          </div>
        </motion.div>
      </footer>
    </div>
  );
};
export default LandingPage;
