#!/bin/bash

echo --- Script START `date`

localonly=no
#localonly=yes

#jobtype=nightly
jobtype=weekly
case "$jobtype" in
    nightly )
	echo --- Nightly job
    ;;
    weekly )
	echo --- Weekly job
    ;;
    * )
# If a new jobtype is added, add support in all similar case statements below    
	echo Unknown jobtype $jobtype
	exit 1
	;;
esac


if [[ $localonly == "yes" ]]; then
echo --- Local CMake/Make/CTest only. No cdash drop.
fi

if [ -e `dirname "$0"`/ornl_update.sh ]; then
    echo --- Updates
    source `dirname "$0"`/ornl_update.sh
fi

if [ -e `dirname "$0"`/ornl_versions.sh ]; then
    source `dirname "$0"`/ornl_versions.sh
else
    echo Did not find version numbers script ornl_versions.sh
    exit 1
fi


plat=`lscpu|grep Vendor|sed 's/.*ID:[ ]*//'`
case "$plat" in
    GenuineIntel )
	ourplatform=Intel
	;;
    AuthenticAMD )
	ourplatform=AMD
	;;
    * )
	# ARM support should be trivial, but is not yet done
	echo Unknown platform
	exit 1
	;;
esac
echo --- Using $ourplatform architecture

ourhostname=`hostname|sed 's/\..*//g'`
echo --- Host is $ourhostname


case "$ourhostname" in
    sulfur )
	if [[ $jobtype == "nightly" ]]; then
	    buildsys="build_gccnew build_intel2020_nompi build_intel2020 build_intel2020_complex build_intel2020_mixed build_intel2020_complex_mixed build_gccnew_nompi_mkl build_gccold_nompi_mkl build_clangnew_nompi_mkl build_gccnew_nompi build_clangnew_nompi build_gccnew_mkl build_gccnew_mkl_complex build_clangnew_mkl build_clangnew_mkl_complex build_clangnew_mkl_mixed build_gcclegacycuda build_gcclegacycuda_complex build_gcclegacycuda_full build_pgi2020_nompi build_clangdev_nompi_mkl"
	else
	    buildsys="build_gccnew_mkl_nompi build_clangnew_mkl_nompi build_intel2020_nompi build_intel2020 build_intel2020_complex build_intel2020_mixed build_intel2020_complex_mixed build_gcclegacycuda build_gcclegacycuda_complex build_pgi2020_nompi"
	fi
    ;;
    nitrogen )
	if [[ $jobtype == "nightly" ]]; then
	    buildsys="build_gccnew build_pgi2020_nompi build_clangdev_nompi build_clangdev_offloadcuda_nompi build_gccnew_nompi build_gccnew_nompi_complex build_clangnew build_clangnew_complex build_clangnew_mixed build_clangnew_complex_mixed build_aompnew_nompi build_aompnew build_aompnew_nompi_mixed build_aompnew_mixed build_aompnew_nompi_complex_mixed build_aompnew_complex_mixed build_aompnew_nompi_complex build_aompnew_complex build_gcclegacycuda build_gcclegacycuda_full build_gcclegacycuda_complex build_gccnew_complex"
	else
	    buildsys="build_gccnew build_pgi2020_nompi build_aompnew_mixed build_gcclegacycuda build_gcclegacycuda_complex build_gccnew_complex build_clangnew build_clangdev_offloadcuda_nompi"
	fi
    ;;
    * )
	echo Unknown host will use gccnew only
	buildsys="build_gccnew"
	;;
esac


case "$jobtype" in
    weekly )
	export GLOBALTCFG="-j 64 --timeout 7200 -VV"
	export LIMITEDTESTS=""
	export LESSLIMITEDTESTS=""
	export QMC_DATA=/scratch/${USER}/QMC_DATA_WEEKLY # Route to directory containing performance test files
	;;
    nightly )
	export GLOBALTCFG="-j 64 --timeout 2400 -VV"
	export LIMITEDTESTS="--tests-regex deterministic -LE unstable -E long-"
	export LESSLIMITEDTESTS="-E long-"
	export QMC_DATA=/scratch/${USER}/QMC_DATA_NIGHTLY # Route to directory containing performance test files
	;;
    * )
	echo Unknown jobtype $jobtype
	exit 1
	;;
esac

# Directory in which to run tests. Should be an absolute path and fastest usable filesystem
test_path=/scratch/${USER}

test_dir=${test_path}/QMCPACK_CI_BUILDS_DO_NOT_REMOVE

export OMP_NUM_THREADS=16

#export PATH=/opt/local/bin:/opt/local/sbin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

# Intel2019.1 MPI configure setting to avoid MPI crash
# via https://software.intel.com/en-us/forums/intel-clusters-and-hpc-technology/topic/799716
#export FI_PROVIDER=sockets
export I_MPI_FABRICS=shm

module() { eval `/usr/bin/modulecmd bash $*`; }

export SPACK_ROOT=$HOME/apps/spack
export PATH=$SPACK_ROOT/bin:$PATH
. $SPACK_ROOT/share/spack/setup-env.sh


echo --- Spack list
spack find
echo --- Modules list
module list
echo --- End listings

spack load git

module list
if [ -e ${test_path} ]; then

if [ ! -e ${test_dir} ]; then
mkdir ${test_dir}
fi

if [ -e ${test_dir} ]; then
cd ${test_dir}

# Minimize load on GitHub by maintaining a local cloned git used for all builds
if [ ! -e qmcpack ]; then
echo --- Cloning QMCPACK git `date`
git clone https://github.com/QMCPACK/qmcpack.git --depth 1
else
cd qmcpack
echo --- Updating local QMCPACK git `date`
git pull
cd ..
fi

# Sanity check cmake config file present
if [ -e qmcpack/CMakeLists.txt ]; then

export PYTHONPATH=${test_dir}/qmcpack/nexus/lib
echo --- PYTHONPATH=$PYTHONPATH
#
# Quantum Espresso setup/download/build
# Future improvement: use spack version or build for more compiler variants
#

export QE_VERSION=6.4.1
sys=build_gccnew
# QE version 6.x unpacks to qe-; Older versions 5.x uses espresso-
export QE_PREFIX=qe-
export QE_BIN=${test_dir}/${sys}_QE/${QE_PREFIX}${QE_VERSION}/bin
echo --- QE_BIN set to ${QE_BIN}
if [ ! -e ${QE_BIN}/pw.x ]; then
    echo --- Downloading and installing patched QE
    # Start from clean build if no executable present
    if [ -e ${test_dir}/${sys}_QE ]; then
	rm -r -f ${test_dir}/${sys}_QE
    fi
    mkdir ${test_dir}/${sys}_QE
		
    cd ${test_dir}/${sys}_QE
    cp -p ../qmcpack/external_codes/quantum_espresso/*${QE_VERSION}* .
    ./download_and_patch_qe${QE_VERSION}.sh
    cd ${QE_PREFIX}${QE_VERSION}

(
    spack load gcc@${gcc_vnew}
    spack load openmpi@${ompi_vnew}
#    if [ "$ourplatform" == "AMD" ]; then
#	spack load amdblis
#	spack load netlib-lapack
#    else
#	spack load blis
#	spack load netlib-lapack
#    fi
#    spack load openblas%gcc@${gcc_vnew} threads=openmp   
    spack load openblas threads=openmp   
    spack load hdf5@${hdf5_vnew}
    spack load --first fftw@${fftw_vnew}
#    ./configure CC=mpicc MPIF90=mpif90 F77=mpif90 BLAS_LIBS=-lblis LAPACK_LIBS=-llapack  --with-scalapack=no --with-hdf5=`spack location -i hdf5@1.10.7`
    ./configure CC=mpicc MPIF90=mpif90 F77=mpif90 BLAS_LIBS=-lopenblas LAPACK_LIBS=-lopenblas  --with-scalapack=no --with-hdf5=`spack location -i hdf5@1.12.0`
    ## GCC10 fortran will abort on argument mismatches in QE MPI unless -fallow-argument-mismatch specified
    cp make.inc make.inc_orig
    sed -i -E 's/(^FFLAGS.*= )/\1 -fallow-argument-mismatch /g' make.inc
    make -j 48 pwall # Parallel build tested OK for pwall with QE 6.4.1. Parallel build of all does NOT work due to broken dependencies
)
    echo -- New QE executable
    ls -l bin/pw.x
    ls -l PW/src/pw.x
    cd ${test_dir}
else
    echo -- Found existing QE ${QE_VERSION} executable
fi
# Finished with QE



#
# PySCF setup
# 

sys=build_gccnew
export PYSCF_HOME=${test_dir}/${sys}_pyscf/pyscf
echo --- PYSCF_HOME set to ${PYSCF_HOME}
if [ ! -e ${PYSCF_HOME}/pyscf/lib/libxc_itrf.so ]; then
    echo --- Downloading and installing PYSCF
# Existence of shared library produced in ~final step of pyscf install as proxy for successful installation
    if [ -e ${test_dir}/${sys}_pyscf ]; then
	rm -r -f ${test_dir}/${sys}_pyscf
    fi
    mkdir ${test_dir}/${sys}_pyscf
		
    cd ${test_dir}/${sys}_pyscf
(

spack load git
spack load gcc@${gcc_vnew}
spack load python@${python_version}%gcc@${gcc_vnew}
spack load --first cmake@${cmake_vnew}%gcc@${gcc_vnew}
#if [ "$ourplatform" == "AMD" ]; then
#    spack load amdblis
#    spack load netlib-lapack
#else
#    spack load blis
#    spack load netlib-lapack
#fi
#spack load openblas%gcc@${gcc_vnew} threads=openmp   
spack load openblas threads=openmp   

git clone https://github.com/pyscf/pyscf.git
cd pyscf
git checkout v1.7.5 # Released 2020-10-04
topdir=`pwd`
here=`pwd`/opt
herelib=`pwd`/opt/lib
mkdir opt
cd opt


echo --- libcint
git clone https://github.com/sunqm/libcint.git
cd libcint
git checkout v4.0.7
mkdir build
cd build
cmake -DWITH_F12=1 -DWITH_RANGE_COULOMB=1 -DWITH_COULOMB_ERF=1 \
    -DCMAKE_INSTALL_PREFIX:PATH=$here -DCMAKE_INSTALL_LIBDIR:PATH=lib ..
make
make install

cd ..
cd ..


echo --- libxc
git clone https://gitlab.com/libxc/libxc.git
cd libxc
git checkout 4.3.4
autoreconf -i
./configure --prefix=$here --libdir=$herelib --enable-vxc --enable-fxc --enable-kxc \
    --enable-shared --disable-static --enable-shared --disable-fortran LIBS=-lm
make
make install
cd ..


echo --- xcfun library
git clone https://github.com/dftlibs/xcfun.git
cd xcfun
git checkout 8ec13b06e06feccbc9e968665977df14d7bfdff8
mkdir build
cd build
cmake -DCMAKE_BUILD_TYPE=RELEASE -DBUILD_SHARED_LIBS=1 -DXC_MAX_ORDER=3 -DXCFUN_ENABLE_TESTS=0 \
    -DCMAKE_INSTALL_PREFIX:PATH=$here -DCMAKE_INSTALL_LIBDIR:PATH=lib ..
make
make install
cd ..
cd ..
echo --- PySCF dependency setup complete
cd ..


echo --- Top level PySCF directory `pwd`
cd pyscf/lib
mkdir build
cd build
cmake -DBUILD_LIBCINT=0 -DBUILD_LIBXC=0 -DBUILD_XCFUN=0 -DCMAKE_INSTALL_PREFIX:PATH=$here ..
make
echo --- PySCF build done
export PYTHONPATH=$topdir:$PYTHONPATH
export LD_LIBRARY_PATH=$herelib:$LD_LIBRARY_PATH
echo export PYTHONPATH=$topdir:\$PYTHONPATH
echo export LD_LIBRARY_PATH=$herelib:\$LD_LIBRARY_PATH

)
    cd ${test_dir}
else
    echo -- Found existing PySCF installation
fi
# Note PYTHONPATH and LD_LIBRARY_PATH are modified in gccnew buildtype below
# Avoids potential incompatibilities with builds from other compiler and library versions
#
# Finished with PySCF setup

echo --- Starting test builds and tests

for sys in $buildsys
do

echo --- START build configuration $sys `date`

cd ${test_dir}

if [ -e $sys ]; then
rm -r -f $sys
fi
mkdir $sys
cd $sys

# Use subshell to allow compiler setup to contaminate the environment
# e.g. No "unload" capability is provided for Intel compiler scripts
(

# Set appropriate environment
if [[ $sys == *"gccnew"* ]]; then
ourenv=gccnewbuild
fi
if [[ $sys == *"gccold"* ]]; then
ourenv=gccoldbuild
fi
if [[ $sys == *"gcclegacycuda"* ]]; then
ourenv=gcclegacycudabuild
fi
if [[ $sys == *"clangnew"* ]]; then
ourenv=clangnewbuild
fi
if [[ $sys == *"clangold"* ]]; then
    # Drop support for old
    echo "*** Support for OLD clang builds dropped 20201223"
    exit 1
    ourenv=clangoldbuild
fi
if [[ $sys == *"clangdev"* ]]; then
ourenv=clangdevbuild
fi
if [[ $sys == *"clanglegacycuda"* ]]; then
ourenv=clanglegacycudabuild
fi
if [[ $sys == *"intel"* ]]; then
ourenv=gccintelbuild
fi
if [[ $sys == *"pgi2020"* ]]; then
ourenv=gccnewbuild
fi
if [[ $sys == *"aompnew"* ]]; then
ourenv=aompnewbuild
fi


spack load git

# Load the modules needed for this type of build
# Choose python on a per build type basis to minimize risk of contamination by e.g. older/newer HDF5 picked up via python modules
case "$ourenv" in
gccnewbuild) echo $ourenv
	spack load gcc@$gcc_vnew
	spack load python%gcc@$gcc_vnew
	spack load --first boost@$boost_vnew%gcc@$gcc_vnew
	spack load hdf5@$hdf5_vnew%gcc@$gcc_vnew
	spack load --first cmake@$cmake_vnew%gcc@$gcc_vnew
	if [[ $sys != *"nompi"* ]]; then
	    spack load openmpi@$ompi_vnew%gcc@$gcc_vnew
	    spack load py-mpi4py%gcc@$gcc_vnew
	fi
	spack load --first libxml2@$libxml2_v%gcc@$gcc_vnew
	spack load --first fftw@$fftw_vnew%gcc@$gcc_vnew
#	if [ "$ourplatform" == "AMD" ]; then
#	    spack load amdblis
#	    spack load netlib-lapack
#	else
#	    spack load blis
#	    spack load netlib-lapack
#	fi
#	spack load openblas%gcc@${gcc_vnew} threads=openmp   
	spack load openblas threads=openmp   
	
	# Make PySCF available
	export PYSCF_BIN=$PYSCF_HOME
	export PYTHONPATH=${test_dir}/build_gccnew_pyscf/pyscf:$PYTHONPATH
	export PYTHONPATH=${test_dir}/qmcpack/utils/afqmctools/:$PYTHONPATH
	export PYTHONPATH=${test_dir}/qmcpack/src/QMCTools/:$PYTHONPATH
	export LD_LIBRARY_PATH=${test_dir}/build_gccnew_pyscf/pyscf/opt/lib:$LD_LIBRARY_PATH
	echo PYSCF_BIN=$PYSCF_HOME
	echo PYTHONPATH=$PYTHONPATH
	echo LD_LIBRARY_PATH=$LD_LIBRARY_PATH
	# For debugging module availability etc. can check if afmctools are working here
	#${test_dir}/qmcpack/utils/afqmctools/bin/pyscf_to_afqmc.py
;;
gccoldbuild) echo $ourenv
	spack load gcc@$gcc_vold
	spack load python%gcc@$gcc_vold
	spack load --first boost@$boost_vold%gcc@$gcc_vold
	spack load hdf5@$hdf5_vold%gcc@$gcc_vold
#	spack load --first cmake@$cmake_vold%gcc@$gcc_vold
	spack load --first cmake@$cmake_vold
	if [[ $sys != *"nompi"* ]]; then
	    spack load openmpi@$ompi_vold%gcc@$gcc_vold
	fi
	spack load --first libxml2@$libxml2_v%gcc@$gcc_vold
	spack load --first fftw@$fftw_vold%gcc@$gcc_vold
#	if [ "$ourplatform" == "AMD" ]; then
#	    spack load amdblis
#	    spack load netlib-lapack
#	else
#	    spack load blis
#	    spack load netlib-lapack
#	fi
#	spack load openblas%gcc@${gcc_vold} threads=openmp   
	spack load openblas threads=openmp   
;;
gcclegacycudabuild) echo $ourenv
	spack load gcc@$gcc_vcuda
	spack load python%gcc@$gcc_vnew
	spack load --first boost@$boost_vnew%gcc@$gcc_vnew
	spack load hdf5@$hdf5_vnew%gcc@$gcc_vnew
	spack load --first cmake@$cmake_vnew%gcc@$gcc_vnew
	if [[ $sys != *"nompi"* ]]; then
	    spack load openmpi@$ompi_vnew%gcc@$gcc_vnew
	fi
	spack load --first libxml2@$libxml2_v%gcc@$gcc_vnew
	spack load --first fftw@$fftw_vnew%gcc@$gcc_vnew
#	if [ "$ourplatform" == "AMD" ]; then
#	    spack load amdblis
#	    spack load netlib-lapack
#	else
#	    spack load blis
#	    spack load netlib-lapack
#	fi
#	spack load openblas%gcc@${gcc_vnew} threads=openmp   
	spack load openblas threads=openmp   
;;
clangnewbuild) echo $ourenv
	spack load llvm@$llvm_vnew
	spack load gcc@$gcc_vnew
	spack load python%gcc@$gcc_vnew
	spack load --first boost@$boost_vnew%gcc@$gcc_vnew
	spack load hdf5@$hdf5_vnew%gcc@$gcc_vnew
	spack load --first cmake@$cmake_vnew%gcc@$gcc_vnew
	if [[ $sys != *"nompi"* ]]; then
	    spack load openmpi@$ompi_vnew%gcc@$gcc_vnew
	fi
	spack load --first libxml2@$libxml2_v%gcc@$gcc_vnew
	spack load --first fftw@$fftw_vnew%gcc@$gcc_vnew
#	if [ "$ourplatform" == "AMD" ]; then
#	    spack load amdblis
#	    spack load netlib-lapack
#	else
#	    spack load blis
#	    spack load netlib-lapack
#	fi
#	spack load openblas%gcc@${gcc_vnew} threads=openmp   
	spack load openblas threads=openmp   
;;
clangdevbuild) echo $ourenv
	spack load llvm@main
	spack load gcc@$gcc_vnew
	spack load python%gcc@$gcc_vnew
	spack load --first boost@$boost_vnew%gcc@$gcc_vnew
	spack load hdf5@$hdf5_vnew%gcc@$gcc_vnew
	spack load --first cmake@$cmake_vnew%gcc@$gcc_vnew
	if [[ $sys != *"nompi"* ]]; then
	    spack load openmpi@$ompi_vnew%gcc@$gcc_vnew
	fi
	spack load --first libxml2@$libxml2_v%gcc@$gcc_vnew
	spack load --first fftw@$fftw_vnew%gcc@$gcc_vnew
#	if [ "$ourplatform" == "AMD" ]; then
#	    spack load amdblis
#	    spack load netlib-lapack
#	else
#	    spack load blis
#	    spack load netlib-lapack
#	fi
#	spack load openblas%gcc@${gcc_vnew} threads=openmp   
	spack load openblas threads=openmp   
;;
aompnewbuild) echo $ourenv
#	spack load llvm@$llvm_vnew
        export PATH=/usr/lib/aomp/bin:$PATH
	spack load gcc@$gcc_vnew
	spack load python%gcc@$gcc_vnew
	spack load --first boost@$boost_vnew%gcc@$gcc_vnew
	spack load hdf5@$hdf5_vnew%gcc@$gcc_vnew
	spack load --first cmake@$cmake_vnew%gcc@$gcc_vnew
	if [[ $sys != *"nompi"* ]]; then
	    spack load openmpi@$ompi_vnew%gcc@$gcc_vnew
	fi
	spack load --first libxml2@$libxml2_v%gcc@$gcc_vnew
	spack load --first fftw@$fftw_vnew%gcc@$gcc_vnew
#	if [ "$ourplatform" == "AMD" ]; then
#	    spack load amdblis
#	    spack load netlib-lapack
#	else
#	    spack load blis
#	    spack load netlib-lapack
#	fi
#	spack load openblas%gcc@${gcc_vnew} threads=openmp   
	spack load openblas threads=openmp   
;;
gccintelbuild) echo $ourenv
	spack load gcc@$gcc_vintel # Provides old enough C++ library for Intel compiler
	spack load python%gcc@$gcc_vnew
	spack load --first boost@$boost_vnew%gcc@$gcc_vnew
	spack load hdf5@$hdf5_vnew%gcc@$gcc_vnew~mpi
	spack load --first cmake@$cmake_vnew%gcc@$gcc_vnew
	spack load --first libxml2@$libxml2_v%gcc@$gcc_vnew
;;
*) echo "Problems: Unknown build environment"
	exit 1
;;
esac
module list

# Construct test name and configure flags
# Compiler and major version, MPI or not
if [[ $sys == *"gcc"* ]]; then
compilerversion=`gcc --version|grep ^gcc|sed 's/^.* //g'|sed 's/\..*//g'`
if [[ $sys == *"nompi"* ]]; then
QMCPACK_TEST_SUBMIT_NAME=GCC${compilerversion}-NoMPI
CTCFG="-DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ -DQMC_MPI=0"
else
QMCPACK_TEST_SUBMIT_NAME=GCC${compilerversion}
CTCFG="-DCMAKE_C_COMPILER=mpicc -DCMAKE_CXX_COMPILER=mpicxx -DQMC_MPI=1"
export OMPI_CC=gcc
export OMPI_CXX=g++

if [[ $sys == *"gccnew"* ]]; then
# Add QE to any gccnew MPI builds
# Restrict to gccnew to avoid problems with mismatched libraries, mpi etc.
CTCFG="$CTCFG -DQE_BIN=${QE_BIN}" 
fi

fi
# On sulfur with gcc builds, workaround presumed AVX512 bug
case "$ourhostname" in
    sulfur )
	echo "Using GCC broadwell architecture override on $ourhostname"
        CTXCFG="-DCMAKE_CXX_FLAGS='-march=broadwell -O3 -DNDEBUG -fomit-frame-pointer -ffast-math';-DCMAKE_C_FLAGS='-march=broadwell -O3 -DNDEBUG -fomit-frame-pointer -ffast-math'"
        ;;
    *)
	echo "No GCC workaround used on this host"
	CTXCFG=""
	;;
esac
echo $CTXCFG
fi

#Clang/LLVM
if [[ $sys == *"clang"* ]]; then
    if [[ $sys == *"clangdev"* ]]; then
	compilerversion=Dev
    else
	compilerversion=`clang --version|grep ^clang|sed -e 's/^.* version //g' -e 's/(.*//g'|sed 's/\..*//g'`
    fi
    if [[ $sys == *"nompi"* ]]; then
	QMCPACK_TEST_SUBMIT_NAME=Clang${compilerversion}-NoMPI
	CTCFG="-DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DQMC_MPI=0"
    else
	QMCPACK_TEST_SUBMIT_NAME=Clang${compilerversion}
	CTCFG="-DCMAKE_C_COMPILER=mpicc -DCMAKE_CXX_COMPILER=mpicxx -DQMC_MPI=1"
	export OMPI_CC=clang
	export OMPI_CXX=clang++
    fi

# Clang OpenMP offload CUDA builds. Setup here due to clang specific arguments
    if [[ $sys == *"offloadcuda"* ]]; then
        QMCPACK_TEST_SUBMIT_NAME=${QMCPACK_TEST_SUBMIT_NAME}-Offload-CUDA
        CTCFG="$CTCFG -DCMAKE_CXX_FLAGS=-Wno-unknown-cuda-version -DQMC_OPTIONS='-DENABLE_OFFLOAD=ON;-DUSE_OBJECT_TARGET=ON;-DENABLE_CUDA=ON;-DCUDA_ARCH=sm_70;-DCUDA_HOST_COMPILER=`which gcc`'"
    fi
fi

#AOMP (fork of Clang/LLVM)
if [[ $sys == *"aomp"* ]]; then
    compilerversion=`aompversion|sed 's/-.*//g'`
    if [[ $sys == *"nompi"* ]]; then
	QMCPACK_TEST_SUBMIT_NAME=AOMP${compilerversion}-Offload-NoMPI
	CTCFG="-DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ -DQMC_MPI=0 -DENABLE_OFFLOAD=ON -DOFFLOAD_TARGET=amdgcn-amd-amdhsa -DOFFLOAD_ARCH=gfx906"
    else
	QMCPACK_TEST_SUBMIT_NAME=AOMP${compilerversion}-Offload
	CTCFG="-DCMAKE_C_COMPILER=mpicc -DCMAKE_CXX_COMPILER=mpicxx -DQMC_MPI=1 -DENABLE_OFFLOAD=ON -DOFFLOAD_TARGET=amdgcn-amd-amdhsa -DOFFLOAD_ARCH=gfx906"
	export OMPI_CC=clang
	export OMPI_CXX=clang++
    fi
fi

# Intel
if [[ $sys == *"intel"* ]]; then

if [[ $sys == *"intel2020"* ]]; then
source /opt/intel2020/bin/compilervars.sh intel64
fi
if [[ $sys == *"intel2019"* ]]; then
source /opt/intel2019/bin/compilervars.sh intel64
fi
if [[ $sys == *"intel2018"* ]]; then
source /opt/intel2018/bin/compilervars.sh intel64
fi
# Assume the Intel dumpversion string has format AA.B.C.DDD
# AA is historically major year and a good enough unique identifier,
# but Intel 2020 packages currently (12/2019) come with the 19.1 compiler.
# Use 19.1 for this compiler only to avoid breaking test histories.
if [[ $sys == *"intel2020"* ]]; then
compilerversion=`icc -dumpversion|sed -e 's/\([0-9][0-9]\)\.\([0-9]\)\..*/\1.\2/g'` # AA.B
else
compilerversion=`icc -dumpversion|sed -e 's/\..*//g'` # AA year only
fi

if [[ $sys == *"nompi"* ]]; then
QMCPACK_TEST_SUBMIT_NAME=Intel20${compilerversion}-NoMPI
CTCFG="-DCMAKE_C_COMPILER=icc -DCMAKE_CXX_COMPILER=icpc -DQMC_MPI=0"
else
QMCPACK_TEST_SUBMIT_NAME=Intel20${compilerversion}
CTCFG="-DCMAKE_C_COMPILER=mpiicc -DCMAKE_CXX_COMPILER=mpiicpc -DQMC_MPI=1"
fi
fi

# NVIDIA HPC SDK / PGI compiler
# Will need future update to use nvcc and nvc++ instead of pgcc and pgc++
# TODO: Ensure consistent CUDA versions used for future pgi+cuda builds
if [[ $sys == *"pgi"* ]]; then
    export NVHPC=/opt/nvidia/hpc_sdk
if [ -e $NVHPC/Linux_x86_64/2020/compilers/bin/nvc++ ]; then
    echo --- Found nvc++ NVIDIA HPC SDK compiler. Adding to PATH
    export PATH=${NVHPC}/Linux_x86_64/2020/compilers/bin:${PATH}
else
    echo --- Did not find expected nvc++ compiler for pgi build. Error.
    exit 1
fi
#compilerversion=`pgcc -V|grep pgcc|sed 's/^pgcc //g'|sed 's/\..*//g'`
compilerversion=`pgcc -V|grep pgcc|sed 's/^pgcc //g'|sed 's/\..*//g'|sed 's/.* //g'`
if [[ $sys == *"nompi"* ]]; then
QMCPACK_TEST_SUBMIT_NAME=PGI20${compilerversion}-NoMPI
CTCFG="-DCMAKE_C_COMPILER=pgcc -DCMAKE_CXX_COMPILER=pgc++ -DQMC_MPI=0"
else
CTCFG="-DCMAKE_C_COMPILER=mpicc -DCMAKE_CXX_COMPILER=mpicxx -DQMC_MPI=1"
export OMPI_CC=pgcc
export OMPI_CXX=pgc++
fi
fi

# Legacy CUDA builds setup
# TODO: Ensure consistent CUDA versions for pgi+cuda, spack sourced compilers etc.
if [[ $sys == *"legacycuda"* ]]; then
export CUDAVER=11.2
if [ -e /usr/local/cuda-${CUDAVER}/bin/nvcc ]; then
    echo --- Found nvcc from CUDA ${CUDAVER} . Adding to PATH
    export PATH=/usr/local/cuda-${CUDAVER}/bin:${PATH}
    export LD_LIBRARY_PATH=/usr/local/cuda-${CUDAVER}/lib64:${LD_LIBRARY_PATH}
else
    echo --- Did not find expected nvcc compiler for CUDA build. Error.
    exit 1
fi
# Specify GPUs for testing. Obtain device IDs via "nvidia-smi -L"
#export CUDA_VISIBLE_DEVICES=
QMCPACK_TEST_SUBMIT_NAME=${QMCPACK_TEST_SUBMIT_NAME}-Legacy-CUDA
CTCFG="$CTCFG -DQMC_CUDA=1"
fi

# MKL
# MKLROOT set in sourced Intel mklvars.sh 
if [[ $sys == *"mkl"* ]]; then
QMCPACK_TEST_SUBMIT_NAME=${QMCPACK_TEST_SUBMIT_NAME}-MKL
# MKL setup used by many builds for BLAS, LAPACK etc.
source /opt/intel2020/mkl/bin/mklvars.sh intel64
fi

# Complex
if [[ $sys == *"complex"* ]]; then
QMCPACK_TEST_SUBMIT_NAME=${QMCPACK_TEST_SUBMIT_NAME}-Complex
CTCFG="$CTCFG -DQMC_COMPLEX=1"
fi

# Mixed/Full precision
if [[ $sys == *"mixed"* ]]; then
QMCPACK_TEST_SUBMIT_NAME=${QMCPACK_TEST_SUBMIT_NAME}-Mixed
CTCFG="$CTCFG -DQMC_MIXED_PRECISION=1"
fi
if [[ $sys == *"full"* ]]; then
QMCPACK_TEST_SUBMIT_NAME=${QMCPACK_TEST_SUBMIT_NAME}-Full
CTCFG="$CTCFG -DQMC_MIXED_PRECISION=0"
fi

# SoA/AoS build (label aos only)
if [[ $sys == *"aos"* ]]; then
QMCPACK_TEST_SUBMIT_NAME=${QMCPACK_TEST_SUBMIT_NAME}-AoS
CTCFG="$CTCFG -DENABLE_SOA=0"
echo "*** ERROR: AoS Builds are deprecated as of 2020-05-19"
exit 1
else
CTCFG="$CTCFG -DENABLE_SOA=1"
fi

# Boilerplate for all tests
CTCFG="$CTCFG -DQMC_DATA=${QMC_DATA} -DENABLE_TIMERS=1"

# Selectively enable AFQMC
if [[ $sys == *"nompi"* ]]; then
    echo "AFQMC is disabled for this build without MPI."
    CTCFG="$CTCFG -DBUILD_AFQMC=0"
else	
    echo "AFQMC is enabled for this complex build"
    CTCFG="$CTCFG -DBUILD_AFQMC=1"
fi



# Adjust which tests are run to control overall runtime
case "$sys" in
*intel2020*|*gccnew*|*clangnew*|*pgi*|*gcccuda|*aompnew_nompi_mixed) echo "Running full ("less limited") test set for $sys"
THETESTS=$LESSLIMITEDTESTS
;;
*) echo "Running limited test set for $sys"
THETESTS=$LIMITEDTESTS
;;
esac
#THETESTS=$LIMITEDTESTS # for DEBUG. Remove for production.
echo $THETESTS

export QMCPACK_TEST_SUBMIT_NAME=${QMCPACK_TEST_SUBMIT_NAME}-Release
echo $QMCPACK_TEST_SUBMIT_NAME
echo $CTCFG
if [[ $localonly == "yes" ]]; then
echo --- START cmake `date` 
cmake ${CTCFG} ${GLOBALTCFG} "$CTXCFG" -DQMC_DATA=${QMC_DATA} -DENABLE_TIMERS=1 ../qmcpack/ 
echo --- END cmake `date`
echo --- START make `date` 
make -j 16
echo --- END make `date`
echo --- START ctest `date` 
#Workaround CUDA concurrency problems
case "$sys" in
    *cuda*)
	ctest ${GLOBALTCFG} ${THETESTS} -DN_CONCURRENT_TESTS=1
	;;
    *)
	ctest -j 48 ${GLOBALTCFG} ${THETESTS}
	;;
esac
echo --- END ctest `date`
else
echo --- START ctest `date` 
echo ctest ${CTCFG} ${GLOBALTCFG} "$CTXCFG" -DQMC_DATA=${QMC_DATA} -DENABLE_TIMERS=1 -S $PWD/../qmcpack/CMake/ctest_script.cmake,release ${THETESTS}
#Workaround CUDA concurrency problems
case "$sys" in
    *cuda*)
	ctest ${CTCFG} ${GLOBALTCFG} "$CTXCFG" -DQMC_DATA=${QMC_DATA} -DENABLE_TIMERS=1 -S $PWD/../qmcpack/CMake/ctest_script.cmake,release ${THETESTS} -DN_CONCURRENT_TESTS=1
	;;
    *)
	ctest -j 48 ${CTCFG} ${GLOBALTCFG} "$CTXCFG" -DQMC_DATA=${QMC_DATA} -DENABLE_TIMERS=1 -S $PWD/../qmcpack/CMake/ctest_script.cmake,release ${THETESTS}
	;;
esac
echo --- END ctest `date`
fi

)

module purge

echo --- END build configuration $sys `date`
done

else
echo "ERROR: No CMakeLists. Bad git clone or update"
exit 1
fi

else
echo "ERROR: Unable to make test directory ${test_dir}"
exit 1
fi

else
echo "ERROR: No directory ${test_path}"
exit 1
fi
echo --- Script END `date`
