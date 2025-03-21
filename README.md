# SVDSuite SVDConv Comparison

This repository is used for evaluating **SVDSuite**. A modified version of `svdconv` is utilized to compare parsing and processing results. In total, results from **3,253 SVD files** (~9.1GB) are compared. All SVD files were extracted from Pack files available at:  
🔗 https://www.keil.com/pack/index.pidx

The file `svd_files.csv` provides an overview of the tested SVD files.


## How to Run

Execute the following command in your shell:

```shell
python main.py <path_to_svd_dir>
```

The target directory must follow this structure:  
`<path_to_svd_dir>/<vendor>.<name>.<version>/<svd>.svd`

The `<vendor>.<name>.<version>` naming follows the same convention used in the Pack files.


## `svdconv` Binary

This repository depends on a **modified version** of `svdconv`. A prebuilt binary is included for convenience. However, if you prefer to build it yourself, follow these steps:

```shell
git clone --recurse-submodules -j8 https://github.com/Open-CMSIS-Pack/devtools.git
cd devtools
git checkout 56f1898
git apply <path_to_this_repo>/svdconv/devtools.patch
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=Debug ..
cmake --build . --config Debug --target svdconv
cp tools/svdconv/SVDConv/linux-amd64/Debug/svdconv <path_to_this_repo>/svdconv/
```