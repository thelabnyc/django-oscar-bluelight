module.exports = {
    plugins: [
        require('autoprefixer')({
            browsers: ['last 2 versions', 'IE 9', 'last 5 ios_saf versions']
        })
    ],
};
