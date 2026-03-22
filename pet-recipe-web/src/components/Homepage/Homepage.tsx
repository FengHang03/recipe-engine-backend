// src/components/Homepage/Homepage.tsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  ChevronRight, 
  Shield, 
  BarChart3, 
  Calculator, 
  Award,
  Heart,
  Users,
  CheckCircle,
  Star,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import AppHeader from '../ui/AppHeader';

const Homepage: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useAuth();

  const handleGetStarted = () => {
    if (currentUser) {
      navigate('/dashboard');
    } else {
      navigate('/login');
    }
  };

  const features = [
    {
      icon: Shield,
      title: 'AAFCO Standards',
      description: 'Strictly follows American Feed Control Association nutritional standards',
      color: 'text-green-600',
      bgColor: 'bg-green-100'
    },
    {
      icon: Calculator,
      title: 'Smart Optimization',
      description: 'Linear programming algorithms ensure optimal balance of nutrition and cost',
      color: 'text-blue-600',
      bgColor: 'bg-blue-100'
    },
    {
      icon: BarChart3,
      title: 'Precise Analysis',
      description: 'Detailed nutritional composition analysis and compliance testing',
      color: 'text-purple-600',
      bgColor: 'bg-purple-100'
    },
    {
      icon: Award,
      title: 'Personalized',
      description: 'Customized formulation based on pet breed, age, and health conditions',
      color: 'text-orange-600',
      bgColor: 'bg-orange-100'
    }
  ];

  const stats = [
    { number: '10,000+', label: 'Nutrition Database' },
    { number: '50+', label: 'Nutrition Metrics' },
    { number: '99%', label: 'AAFCO Compliance' },
    { number: '30s', label: 'Generation Time' }
  ];

  const testimonials = [
    {
      name: 'Sarah Johnson',
      pet: 'Golden Retriever Max',
      content: 'The recipe is very scientific. After Max ate it for a few months, his coat became shinier and his weight is well controlled.',
      rating: 5
    },
    {
      name: 'Michael Chen',
      pet: 'British Shorthair Luna',
      content: 'I used to worry about homemade cat food not being nutritious enough. Now with professional recipes, I feel much more at ease.',
      rating: 5
    },
    {
      name: 'Dr. Emily Wang',
      pet: 'Poodle Belle',
      content: 'As a veterinarian, I think this system\'s nutritional analysis is very professional. I recommend it to my clients.',
      rating: 5
    }
  ];

  return (
    <div className="min-h-screen">
      {/* 共享导航栏 */}
      <AppHeader />

      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 lg:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <motion.h1
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              className="text-4xl md:text-6xl font-bold text-gray-900 mb-6"
            >
              Scientific Formulation
              <span className="text-green-600 block mt-2">Professional Pet Fresh Food Recipes</span>
            </motion.h1>
            
            <motion.p
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto leading-relaxed"
            >
              Based on AAFCO nutritional standards, using linear programming algorithms to create customized, nutritionally balanced and cost-optimized fresh food recipes for your beloved pets
            </motion.p>
            
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="flex flex-col sm:flex-row gap-4 justify-center mb-16"
            >
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleGetStarted}
                className="bg-green-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-green-700 transition-colors shadow-lg flex items-center justify-center space-x-2"
              >
                <span>{currentUser ? 'Go to Dashboard' : 'Start Creating Recipe'}</span>
                <ChevronRight className="w-5 h-5" />
              </motion.button>
              
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  // TODO: 实现查看示例食谱功能
                  alert('Sample recipe feature coming soon!');
                }}
                className="border border-gray-300 text-gray-700 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-gray-50 transition-colors"
              >
                View Sample Recipe
              </motion.button>
            </motion.div>

            {/* Stats */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.6 }}
              className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-20"
            >
              {stats.map((stat, index) => (
                <div key={index} className="text-center">
                  <div className="text-3xl font-bold text-green-600 mb-2">
                    {stat.number}
                  </div>
                  <div className="text-gray-600 text-sm">
                    {stat.label}
                  </div>
                </div>
              ))}
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Why Choose Our Recipe System?
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Combining professional nutritional knowledge with modern algorithmic technology to provide the most scientific dietary solutions for your beloved pets
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                  viewport={{ once: true }}
                  className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
                >
                  <div className={`w-12 h-12 ${feature.bgColor} rounded-lg flex items-center justify-center mb-4`}>
                    <Icon className={`w-6 h-6 ${feature.color}`} />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600 text-sm">
                    {feature.description}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Get Professional Recipe in Three Steps
            </h2>
            <p className="text-xl text-gray-600">
              Simple steps to generate professional nutritional recipes for your beloved pets
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: '01',
                title: 'Enter Pet Information',
                description: 'Tell us your pet\'s basic information: breed, age, weight, activity level, etc.',
                icon: Heart
              },
              {
                step: '02',
                title: 'AI Smart Analysis',
                description: 'System performs nutritional optimization based on AAFCO standards using linear programming algorithms',
                icon: Calculator
              },
              {
                step: '03',
                title: 'Get Professional Recipe',
                description: 'Generate detailed recipe within 30 seconds, including nutritional analysis, preparation guidance and cost calculation',
                icon: CheckCircle
              }
            ].map((item, index) => {
              const Icon = item.icon;
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: index * 0.2 }}
                  viewport={{ once: true }}
                  className="text-center"
                >
                  <div className="relative mb-6">
                    <div className="w-16 h-16 bg-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Icon className="w-8 h-8 text-white" />
                    </div>
                    <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 -translate-y-full w-8 h-8 bg-white border-2 border-green-600 rounded-full flex items-center justify-center">
                      <span className="text-green-600 font-bold text-sm">{item.step}</span>
                    </div>
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-3">
                    {item.title}
                  </h3>
                  <p className="text-gray-600">
                    {item.description}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section id="testimonials" className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Real User Feedback
            </h2>
            <p className="text-xl text-gray-600">
              See how other pet owners evaluate our recipe system
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                viewport={{ once: true }}
                className="bg-white p-6 rounded-xl shadow-sm border border-gray-100"
              >
                <div className="flex items-center mb-4">
                  {[...Array(testimonial.rating)].map((_, i) => (
                    <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />
                  ))}
                </div>
                <p className="text-gray-700 mb-4">
                  "{testimonial.content}"
                </p>
                <div className="flex items-center">
                  <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center mr-3">
                    <Users className="w-5 h-5 text-gray-600" />
                  </div>
                  <div>
                    <div className="font-semibold text-gray-900">{testimonial.name}</div>
                    <div className="text-sm text-gray-600">{testimonial.pet}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-green-600">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl font-bold text-white mb-4">
              Generate Professional Recipe in 30 Seconds
            </h2>
            <p className="text-xl text-green-100 mb-8">
              Simply enter your pet's basic information, and our AI system will generate scientific recipes that meet nutritional standards
            </p>
            
            <div className="flex flex-col sm:flex-row gap-6 items-center justify-center mb-8">
              <div className="flex items-center space-x-2 text-green-100">
                <CheckCircle className="w-5 h-5" />
                <span className="text-sm font-medium">Real-time Nutrition Analysis</span>
              </div>
              <div className="flex items-center space-x-2 text-green-100">
                <CheckCircle className="w-5 h-5" />
                <span className="text-sm font-medium">Cost Optimization Calculation</span>
              </div>
              <div className="flex items-center space-x-2 text-green-100">
                <CheckCircle className="w-5 h-5" />
                <span className="text-sm font-medium">Preparation Guidance</span>
              </div>
            </div>

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleGetStarted}
              className="bg-white text-green-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-gray-50 transition-colors shadow-lg flex items-center justify-center space-x-2 mx-auto"
            >
              <span>Start Creating Now</span>
              <ChevronRight className="w-5 h-5" />
            </motion.button>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <h3 className="text-lg font-semibold mb-4">Pet Recipe Generator</h3>
              <p className="text-gray-400 text-sm">
                Professional pet nutrition powered by AAFCO standards and AI technology.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#features" className="hover:text-white">Features</a></li>
                <li><a href="#how-it-works" className="hover:text-white">How It Works</a></li>
                <li><a href="#testimonials" className="hover:text-white">Testimonials</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#" className="hover:text-white">About Us</a></li>
                <li><a href="#" className="hover:text-white">Contact</a></li>
                <li><a href="#" className="hover:text-white">Privacy Policy</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Support</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li><a href="#" className="hover:text-white">Help Center</a></li>
                <li><a href="#" className="hover:text-white">FAQ</a></li>
                <li><a href="#" className="hover:text-white">Contact Support</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-sm text-gray-400">
            <p>&copy; 2024 Pet Recipe Generator. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Homepage;
