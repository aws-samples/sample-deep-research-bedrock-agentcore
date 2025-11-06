module.exports = {
  webpack: {
    configure: (webpackConfig) => {
      // Fix for webpack 5 polyfills
      webpackConfig.resolve.fallback = {
        ...webpackConfig.resolve.fallback,
        "process": require.resolve("process/browser"),
        "buffer": require.resolve("buffer/")
      };
      return webpackConfig;
    }
  }
};
