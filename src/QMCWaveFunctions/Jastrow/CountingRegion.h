#ifndef QMC_PLUS_PLUS_COUNTING_FUNCTOR_H
#define QMC_PLUS_PLUS_COUNTING_FUNCTOR_H

#include "Configuration.h"
#include "QMCWaveFunctions/Jastrow/CountingFunctor.h"
#include "Particle/ParticleSet.h"

namespace qmcplusplus
{

// T is precision

template <class T> class NormalizedGaussianRegion: public QMCTraits
{
  
public:
  typedef GaussianFunctor<T> FunctorType;
  // counting function pointers
  std::vector<FunctorType*> C;

protected:
  RealType Nval_t;

  // reference gaussian id, pointer 
  std::string Cref_id;
  FunctorType* Cref;

  // number of electrons
  int num_els;
  // number of regions
  int num_regions;
  // counting function id
  std::vector<std::string> C_id;

  // value arrays
  std::vector<RealType> _val;
  std::vector<RealType> _sum;
  std::vector<GradType> _grad;
  std::vector<RealType> _lap;
  std::vector<RealType> Nval;

  // log values arrays
  std::vector<RealType> _Lval;
  std::vector<GradType> _Lgrad;
  std::vector<RealType> _Llap;
  std::vector<RealType> Lmax; 

  // temporary value arrays
  std::vector<RealType> _val_t;
  std::vector<RealType> _sum_t;
  std::vector<GradType> _grad_t;
  std::vector<RealType> _lap_t;
  
  //memory for temporary log value arrays
  std::vector<RealType> _Lval_t;
  std::vector<GradType> _Lgrad_t;
  std::vector<RealType> _Llap_t;
  RealType Lmax_t;

  std::vector<RealType> _dLval_saved;


public: 
  NormalizedGaussianRegion(ParticleSet& P)
  {
    num_els = P.getTotalNum();
  }

  const bool normalized = true; // flag for normalized regions
  int size() const                  { return num_regions; }
  const opt_variables_type& getVars(int I) {return C[I]->myVars;}
  int max_num_derivs() const   
  { 
    auto comp = [](FunctorType* a, FunctorType* b){ return a->myVars.size() < b->myVars.size(); };
    FunctorType* Cmax = *(std::max_element(C.begin(),C.end(),comp));
    return Cmax->myVars.size();
  }

  // sum/grad/lap getters: index convention defined in base
  inline RealType& val(int I, int i)  { return _val[I*num_els + i]; }
  inline RealType& sum(int I)         { return _sum[I]; }
  inline GradType& grad(int I, int i) { return _grad[I*num_els + i]; }
  inline RealType& lap(int I, int i)  { return _lap[I*num_els + i]; }
  inline RealType& val_t(int I)       { return _val_t[I]; }
  inline RealType& sum_t(int I)       { return _sum_t[I]; }
  inline GradType& grad_t(int I)      { return _grad_t[I]; }
  inline RealType& lap_t(int I)       { return _lap_t[I]; }

  inline RealType& Lval(int I, int i)  { return _Lval[I*num_els + i]; }
  inline GradType& Lgrad(int I, int i) { return _Lgrad[I*num_els + i]; }
  inline RealType& Llap(int I, int i)  { return _Llap[I*num_els + i]; }

  inline RealType& Lval_t(int I)  { return _Lval_t[I]; }
  inline GradType& Lgrad_t(int I) { return _Lgrad_t[I]; }
  inline RealType& Llap_t(int I)  { return _Llap_t[I]; }
  inline RealType& dLval_saved(int I, int p, int i)  { return _dLval_saved[I*max_num_derivs()*num_els + p*num_els + i]; }

  void addFunc(FunctorType* func, std::string fid)
  {
    C_id.push_back(fid);
    C.push_back(func);
  }

  void initialize()
  { 
    app_log() << "NormalizedGaussianRegion::initialize" << std::endl;
    num_regions = C.size();
    // resize arrays
    _val.resize(num_regions*num_els);
    _sum.resize(num_regions);
    _grad.resize(num_regions*num_els);
    _lap.resize(num_regions*num_els);
    Nval.resize(num_els);

    _val_t.resize(num_regions);
    _sum_t.resize(num_regions);
    _grad_t.resize(num_regions);
    _lap_t.resize(num_regions);

    _Lval.resize(num_regions*num_els);
    _Lgrad.resize(num_regions*num_els);
    _Llap.resize(num_regions*num_els);
    Lmax.resize(num_els);

    _Lval_t.resize(num_regions);
    _Lgrad_t.resize(num_regions);
    _Llap_t.resize(num_regions);
    _dLval_saved.resize(max_num_derivs()*num_regions*num_els);
    // store log derivative values for single particle moves
  }

  void checkInVariables(opt_variables_type& active)
  {
    for(auto it = C.begin(); it != C.end(); ++it)
      (*it)->checkInVariables(active);
  }
  void checkOutVariables(const opt_variables_type& active) 
  {
    for(auto it = C.begin(); it != C.end(); ++it)
      (*it)->checkOutVariables(active);
  }
  void resetParameters(const opt_variables_type& active)
  {
    for(auto it = C.begin(); it != C.end(); ++it)
      (*it)->resetParameters(active);
  }

  void acceptMove(ParticleSet& P, int iat)
  {
    Nval[iat] = Nval_t;
    Lmax[iat] = Lmax_t;
    for(int I = 0; I < num_regions; ++I)
    {
      sum(I) = sum_t(I); 
      val(I,iat) = val_t(I);
      grad(I,iat) = grad_t(I);
      lap(I,iat) = lap_t(I);

      Lval(I,iat) = Lval_t(I);
      Lgrad(I,iat) = Lgrad_t(I);
      Llap(I,iat) = Llap_t(I);
    }
  }

  void restore(int iat) 
  {
    for(int I = 0; I < C.size(); ++I)
      C[I]->restore(iat);
  }

  void reportStatus(std::ostream& os)
  {
    // print some class variables:
    os << "NormalizedGaussianRegion::reportStatus begin" << std::endl;
    os << "num_els: " << num_els << ", num_regions: " << num_regions << std::endl;
    os << "Counting Functions: " << std::endl;
    for(int I = 0; I < C.size(); ++I)
      C[I]->reportStatus(os);
    os << "NormalizedGaussianRegion::reportStatus end" << std::endl;
  }

  NormalizedGaussianRegion* makeClone()
  {
    NormalizedGaussianRegion* cr = new NormalizedGaussianRegion(num_els);
    // copy class variables set in put()
//    cr->C_id.resize( C_id.size() );
//    cr->C.resize( C.size() );
//    for(int i = 0; i < C.size(); ++i)
//    {
//      cr->C_id[i] = std::string(C_id[i]);
//      cr->C[i] = C[i]->makeClone(C_id[i]);
//    }
    for(int i = 0; i < C.size(); ++i)
    {
//      FunctorType* Ci = C[i]->makeClone(C_id[i]);
      FunctorType* Ci = C[i]->makeClone();
      cr->addFunc(Ci, C_id[i]);
    }
    // initialize
    cr->initialize();
    return cr;
  } 

  bool put(xmlNodePtr cur)
  {
    // get the reference function
    OhmmsAttributeSet rAttrib;
    Cref_id = "none";
    rAttrib.add(Cref_id,"reference_id");
    rAttrib.put(cur);
    // loop through array, find where Cref is
    auto C_id_it = std::find(C_id.begin(),C_id.end(),Cref_id);
    int ref_index = std::distance(C_id.begin(),C_id_it);
    if(Cref_id == "none" || C_id_it == C_id.end())
      APP_ABORT("NormalizedGaussianRegion::put: reference function not found:"+ (Cref_id == "none"?" Cref not specified":"\"" + Cref_id + "\"")); 
    // make a copy of the reference gaussian
    Cref = C[ref_index]->makeClone(Cref_id + "_ref");


    // divide all gaussians by the reference
    for(auto it = C.begin(); it != C.end(); ++it)
    {
      (*it)->divide_eq(Cref);
    }
    initialize();
    return true;
  }

  // evaluate using the log of the counting basis
  void evaluate(ParticleSet& P)
  {
    // clear arrays
    std::fill(_val.begin(),_val.end(),0);
    std::fill(_sum.begin(),_sum.end(),0);
    std::fill(_grad.begin(),_grad.end(),0);
    std::fill(_lap.begin(),_lap.end(),0);
    std::fill(_Lval.begin(),_Lval.end(),0);
    std::fill(_Lgrad.begin(),_Lgrad.end(),0);
    std::fill(_Llap.begin(),_Llap.end(),0);
    std::fill(Nval.begin(),Nval.end(),0);
    std::fill(Lmax.begin(),Lmax.end(),0);
    // temporary variables: Lval = ln(C), Lgrad = \nabla ln(C), Llap = \nabla^2 ln(C)
    for(int i = 0; i < num_els; ++i)
    {
      for(int I = 0; I < num_regions; ++I)
      {
        C[I]->evaluateLog(P.R[i],Lval(I,i),Lgrad(I,i),Llap(I,i));
        if(Lval(I,i) > Lmax[i])
          Lmax[i] = Lval(I,i);

      }
      // build counting function values; subtract off largest log value
      for(int I = 0; I < num_regions; ++I)
      {
        val(I,i) = std::exp(Lval(I,i) - Lmax[i]);
        Nval[i] += val(I,i);
      }
      GradType gLN_sum = 0; // \sum\limits_I \nabla L_{Ii} N_{Ii}
      RealType lLN_sum = 0; // \sum\limits_I \nabla^2 L_{Ii} N_{Ii}
      // build normalized counting function value, intermediate values for gradient
      for(int I = 0; I < num_regions; ++I)
      {
        val(I,i) = val(I,i) / Nval[i];
        sum(I) += val(I,i);
        gLN_sum += Lgrad(I,i) * val(I,i);
        lLN_sum += Llap(I,i) * val(I,i);
      }
      RealType gLgN_sum = 0; // \sum\limits_{I} \nabla L_{Ii} \cdot \nabla N_{Ii}
      // build gradient, intermediate values for laplacian
      for(int I = 0; I < num_regions; ++I)
      {
        grad(I,i) = (Lgrad(I,i) - gLN_sum)*val(I,i);
        gLgN_sum += dot(Lgrad(I,i), grad(I,i));
      }
      //build laplacian
      for(int I = 0; I < num_regions; ++I)
      {
        lap(I,i) = (Llap(I,i) - lLN_sum - gLgN_sum)*val(I,i) + dot(grad(I,i),Lgrad(I,i) - gLN_sum);
      }
    }
  }

  void evaluate_print(std::ostream& os, ParticleSet& P)
  {
    for(auto it = C.begin(); it != C.end(); ++it)
      (*it)->evaluate_print(os,P);
    os << "NormalizedGaussianRegions::evaluate_print" << std::endl;
    os << "val: ";
    std::copy(_val.begin(),_val.end(),std::ostream_iterator<RealType>(os,", "));
    os << std::endl << "sum: ";
    std::copy(_sum.begin(),_sum.end(),std::ostream_iterator<RealType>(os,", "));
    os << std::endl << "grad: ";
    std::copy(_grad.begin(),_grad.end(),std::ostream_iterator<GradType>(os,", "));
    os << std::endl << "lap: ";
    std::copy(_lap.begin(),_lap.end(),std::ostream_iterator<RealType>(os,", "));
    os << std::endl << "Nval: ";
    std::copy(Nval.begin(),Nval.end(),std::ostream_iterator<RealType>(os,", "));
    os << std::endl << "Lmax: "; 
    std::copy(Lmax.begin(), Lmax.end(), std::ostream_iterator<RealType>(os,", "));
    os << std::endl;
  }
 

  void evaluateTemp(ParticleSet& P, int iat)
  {
    // clear arrays
    std::fill(_val_t.begin(),_val_t.end(),0);
    std::fill(_sum_t.begin(),_sum_t.end(),0);
    std::fill(_grad_t.begin(),_grad_t.end(),0);
    std::fill(_lap_t.begin(),_lap_t.end(),0);
    std::fill(_Lval_t.begin(),_Lval_t.end(),0);
    std::fill(_Lgrad_t.begin(),_Lgrad_t.end(),0);
    std::fill(_Llap_t.begin(),_Llap_t.end(),0);

    Lmax_t = Lmax[iat];
    Nval_t = 0;
    // temporary variables
    for(int I = 0; I < num_regions; ++I)
    {
      C[I]->evaluateLog(P.R[iat],Lval_t(I),Lgrad_t(I),Llap_t(I));
      if(Lval_t(I) > Lmax_t)
        Lmax_t = Lval_t(I);
    }
    // build counting function values; subtract off largest log value
    for(int I = 0; I < num_regions; ++I)
    {
      val_t(I) = std::exp(Lval_t(I) - Lmax_t);
      Nval_t += val_t(I);
    }
    GradType gLN_sum_t = 0; // \sum\limits_I \nabla L_{Ii} N_{Ii}
    RealType lLN_sum_t = 0; // \sum\limits_I \nabla^2 L_{Ii} N_{Ii}
    // build normalized counting function value, intermediate values for gradient
    for(int I = 0; I < num_regions; ++I)
    {
      val_t(I) = val_t(I) / Nval_t;
      sum_t(I) = sum(I) + val_t(I) - val(I,iat);
      gLN_sum_t += Lgrad_t(I) * val_t(I);
      lLN_sum_t += Llap_t(I) * val_t(I);
    }
    RealType gLgN_sum_t = 0; // \sum\limits_{I} \nabla L_{Ii} \cdot \nabla N_{Ii}
    // build gradient, intermediate values for laplacian
    for(int I = 0; I < num_regions; ++I)
    {
      grad_t(I) = (Lgrad_t(I) - gLN_sum_t)*val_t(I);
      gLgN_sum_t += dot(Lgrad_t(I), grad_t(I));
    }
    //build laplacian
    for(int I = 0; I < num_regions; ++I)
    {
      lap_t(I) = (Llap_t(I) - lLN_sum_t - gLgN_sum_t)*val_t(I) + dot(grad_t(I), Lgrad_t(I) - gLN_sum_t);
    }
    
  }

  void evaluateTemp_print(std::ostream& os, ParticleSet& P)
  {
    for(auto it = C.begin(); it != C.end(); ++it)
      (*it)->evaluate_print(os,P);
    os << "NormalizedGaussianRegion::evaluateTemp_print" << std::endl;
    os << "val_t: ";
    std::copy(_val_t.begin(),_val_t.end(),std::ostream_iterator<RealType>(os,", "));
    os << std::endl << "sum_t: ";
    std::copy(_sum_t.begin(),_sum_t.end(),std::ostream_iterator<RealType>(os,", "));
    os << std::endl << "grad_t: ";
    std::copy(_grad_t.begin(),_grad_t.end(),std::ostream_iterator<GradType>(os,", "));
    os << std::endl << "lap_t: ";
    std::copy(_lap_t.begin(),_lap_t.end(),std::ostream_iterator<RealType>(os,", "));
    os << std::endl << "Nval_t: " << Nval_t;
    os << std::endl << "Lmax_t: " << Lmax_t;
    os << std::endl;
  }



  // calculates derivatives of single particle move of particle with index iat
  void evaluateTempDerivatives(ParticleSet& P, 
                               const int I, // index of the counting function parameter derivatives are associated with
                               int iat,
                               std::function<RealType&(int,int)> dNdiff)
  {
    // may assume evaluate and evaluateTemp has already been called
    int num_derivs = getVars(I).size();
    // get log derivatives
    static std::vector<RealType> dLval_t;
    static int mnd = max_num_derivs();
    dLval_t.resize(mnd);

    C[I]->evaluateLogTempDerivatives(P.R[iat], dLval_t);
    for(int J = 0; J < num_regions; ++J)
    {
      for(int p = 0; p < num_derivs; ++p)
      {
        RealType val_Ii = (I==J) - val(I,iat);
        RealType val_It = (I==J) - val_t(I);
        dNdiff(J,p) = val_t(J)*dLval_t[p]*val_It - val(J,iat)*dLval_saved(I,p,iat)*val_Ii;
      }
    }
  }

  void evaluateDerivatives(ParticleSet& P, 
                          int I, 
                          std::function<const GradType&(int,int)> FCgrad, 
                          std::function<RealType&(int,int)> dNsum, 
                          std::function<RealType&(int,int)> dNggsum,
                          std::function<RealType&(int,int)> dNlapsum, 
                          std::vector<RealType>& dNFNggsum)
  {
    evaluate(P);
    static std::vector<RealType> dLval;
    static std::vector<GradType> dLgrad;
    static std::vector<RealType> dLlap;
    static int mnd = max_num_derivs();
    dLval.resize(mnd);
    dLgrad.resize(mnd);
    dLlap.resize(mnd);

    int num_derivs = getVars(I).size();
    for(int i = 0; i < num_els; ++i)
    {
      // get log derivatives
      //C[I]->evaluateLogDerivatives(P.R[i], dCval, dLgrad, dLlap);
      C[I]->evaluateLogDerivatives(P.R[i], dLval, dLgrad, dLlap);
      for(int J = 0; J < num_regions; ++J)
      {
        for(int p = 0; p < num_derivs; ++p)
        {
          RealType val_Ii = (I==J) - val(I,i);

          RealType dNval = val(J,i)*dLval[p]*val_Ii;
          GradType dNgrad = grad(J,i)*dLval[p]*val_Ii + val(J,i)*dLgrad[p]*val_Ii  - val(J,i)*dLval[p]*grad(I,i);

          RealType dNlap = lap(J,i)*dLval[p]*val_Ii + 2*dot(grad(J,i),dLgrad[p])*val_Ii - 2*dot(grad(J,i),grad(I,i))*dLval[p] 
                                                      + val(J,i)*dLlap[p]*val_Ii          - 2*val(J,i)*dot(dLgrad[p],grad(I,i)) 
                                                                                          - val(J,i)*dLval[p]*lap(I,i);         
          // accumulate
          dLval_saved(I,p,i) = dLval[p];
          dNsum(J,p) += dNval;
          dNggsum(J,p) += dot(dNgrad, P.G[i]);
          dNlapsum(J,p) += dNlap;
          dNFNggsum[p] += dot(dNgrad, FCgrad(J,i));
        }
      }
    }
  } // end evaluateDerivatives

};




//template <class T> class SigmoidRegion
//{
//public:
//  typedef SigmoidFunctor<T> FunctorType;
//
//  // variables
//
//  // constructor
//  SigmoidRegion(ParticleSet& targetPtcl)
//  {
//  }
//
//  // destructor
//  ~SigmoidRegion()
//  {}
//
//  void addFunc(FunctorType* func, std::string id);
//  //void addFunc( );
//};

}
#endif
