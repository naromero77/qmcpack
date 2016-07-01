
import os
from numpy import ndarray
from developer import obj,ci,error as dev_error,devlog,DevBase
from pwscf import generate_pwscf
from qmcpack_converters import generate_pw2qmcpack
from qmcpack_input import generate_jastrow,loop,linear,cslinear,vmc,dmc
from qmcpack import generate_qmcpack


def error(msg,loc=None,exit=True,trace=True,indent='    ',logfile=devlog):
    header = 'qmcpack_workflows'
    if loc!=None:
        msg+='\nfunction location: {0}'.format(loc)
    #end if
    dev_error(msg,header,exit,trace,indent,logfile)
#end def error



defaults_version = 'v1'


def hashable(v):
    try:
        hash(v)
    except:
        return False
    #end try
    return True
#end def hashable


class Missing:
    def __call__(self,value):
        return isinstance(value,Missing)
    #end def __call__
#end class Missing
missing = Missing()


class CallBase(object):
    strict = True
    defs   = obj()
    location = 'unknown location'
#end class CallBase


class Defaults(CallBase):
    def __call__(self,name,value):
        if not missing(value):
            return value
        elif name in self.defs:
            return self.defs[name]
        elif self.strict:
            error('default value is missing for variable named {0}'.format(name),self.location)
        #end if
    #end def __call__
#end class Defaults
default = Defaults()


class Requirement(CallBase):
    def __call__(self,name,value):
        if missing(value):
            error('a value has not been provided for required variable named {0}'.format(name),self.location)
        #end if
        return value
    #end def __call__
#end class Requirement
require = Requirement()


class Assignment(CallBase):
    def __call__(self,o,name,value):
        if not missing(value):
            o[name] = value
        #end if
    #end def __call__
#end class Assignment
assign = Assignment()


class RequireAssignment(CallBase):
    def __call__(self,o,name,value):
        if missing(value):
            error('a value has not been provided for required variable named {0}'.format(name),self.location)
        #end if
        o[name] = value
    #end def __call__
#end class RequireAssignment
assign_require = RequireAssignment()


class DefaultAssignment(CallBase):
    def __call__(self,o,name,value):
        if not missing(value):
            o[name] = value
        elif name in self.defs:
            o[name] = self.defs[name]
        elif self.strict:
            error('default value is missing for variable named {0}'.format(name),self.location)
        #end if
    #end def __call__
#end class DefaultAssignment
assign_default = DefaultAssignment()


def set_def_loc(defs,loc,strict=True):
    CallBase.defs     = defs
    CallBase.location = loc
    CallBase.strict   = strict
#end def set_def_loc


def set_loc(loc):
    CallBase.location = loc
#end def set_loc


def assign_defaults(o,defs):
    for name,value in defs.iteritems():
        if name not in o:
            o[name] = value
        #end if
    #end for
#end def assign_defaults


def extract_keywords(o,names,optional=False):
    k = obj()
    if not optional:
        missing = set(names)-set(o.keys())
        if len(missing)>0:
            error('keywords are missing, please provide them\nmissing keywords: {0}\nfunction location: {1}'.format(sorted(missing),CallBase.location))
        #end if
        for name in names:
            k[name] = o[name]
            del o[name]
        #end for
    else:
        for name in names:
            if name in o:
                k[name] = o[name]
                del o[name]
            #end if
        #end for
    #end if
    return k
#end def extract_keywords


def prevent_invalid_input(invalid,loc):
    if len(invalid)>0:
        if isinstance(invalid,(dict,obj)):
            invalid = invalid.keys()
        #end if
        error('invalid input keywords encountered\ninvalid keywords: {0}\nfunction location: {1}'.format(sorted(invalid),loc))
    #end if
#end def prevent_invalid_input





jastrow_factor_keys = ['J1','J2','J3',
                       'J1_size','J1_rcut',
                       'J2_size','J2_rcut','J2_init',
                       'J3_isize','J3_esize','J3_rcut',
                       'J1_rcut_open','J2_rcut_open']
jastrow_factor_defaults = obj(
    v1 = obj(
        J1           = True,
        J2           = True,
        J3           = False,
        J1_size      = 10,
        J1_rcut      = None,
        J2_size      = 10,
        J2_rcut      = None,
        J2_init      = 'zero',
        J3_isize     = 3,
        J3_esize     = 3,
        J3_rcut      = 5.0,
        J1_rcut_open = 5.0,
        J2_rcut_open = 10.0,
        ),
    )



opt_sections_keys = [
    'method','cost','cycles','var_cycles','opt_calcs','blocks',
    'warmupsteps','stepsbetweensamples','timestep','samples',
    'minwalkers','maxweight','usedrift','minmethod','beta',
    'exp0','bigchange','alloweddifference','stepsize',
    'stabilizerscale','nstabilizers','max_its','cgsteps',
    'eigcg','walkers','nonlocalpp','usebuffer','gevmethod',
    'steps','substeps','stabilizermethod','cswarmupsteps',
    'alpha_error','gevsplit','beta_error'
    ]



opt_sections_defaults = obj(
    v1 = obj(
        method     = 'linear',
        cost       = 'variance',
        cycles     = 12,
        var_cycles = 4,
        defaults   = defaults_version,
        ),
    )


opt_method_defaults = obj(
    linear = obj(
        mm = obj(
            samples           = 128000,  
            warmupsteps       = 25, 
            blocks            = 250,  
            steps             = 1, 
            substeps          = 20, 
            timestep          = 0.5, 
            usedrift          = True, 
            nonlocalpp        = True, 
            usebuffer         = True, 
            minmethod         = 'quartic',
            exp0              = -6,
            bigchange         = 10.0,
            alloweddifference = 1.0e-5, 
            stepsize          = 0.15, 
            nstabilizers      = 1, 
            ),
        yl = obj(
            walkers             = 256, 
            samples             = 655360,  
            warmupsteps         = 1, 
            blocks              = 40, 
            substeps            = 5,     
            stepsbetweensamples = 1, 
            timestep            = 1.0,  
            usedrift            = False, 
            nonlocalpp          = False,
            usebuffer           = False,
            minmethod           = 'quartic',
            gevmethod           = 'mixed',
            minwalkers          = 0.3, 
            maxweight           = 1e9, 
            stepsize            = 0.9, 
            ),
        v1 = obj(
            samples           = 204800,             
            warmupsteps       = 300,                
            blocks            = 100,                
            steps             = 1,                  
            substeps          = 10,                 
            timestep          = 0.3,
            usedrift          = False,                 
            nonlocalpp        = True,                
            usebuffer         = True,                
            minmethod         = 'quartic',            
            exp0              = -6,                 
            bigchange         = 10.0,               
            alloweddifference = 1e-05,              
            stepsize          = 0.15,               
            nstabilizers      = 1,                  
            ),
        ),
    cslinear = obj(
        ls = obj(
            warmupsteps       = 20,
            steps             = 5,
            usedrift          = True,
            timestep          = .8,
            nonlocalpp        = False,
            minmethod         = 'rescale',
            stepsize          = .4,
            beta              = .05,
            gevmethod         = 'mixed',
            alloweddifference = 1e-4,
            bigchange         = 9.,
            exp0              = -16,
            max_its           = 1,
            maxweight         = 1e9,
            minwalkers        = .5,
            nstabilizers      = 3,
            stabilizerscale   = 1,
            usebuffer         = False,
            ),
        jm = obj(
            warmupsteps       = 20,
            usedrift          = True,
            timestep          = .5,
            nonlocalpp        = True,
            minmethod         = 'quartic',
            stepsize          = .4,
            beta              = 0.0,
            gevmethod         = 'mixed',
            alloweddifference = 1.0e-4,
            bigchange         = 9.0,
            exp0              = -16,
            max_its           = 1,
            maxweight         = 1e9,
            minwalkers        = 0.5,
            nstabilizers      = 3,
            stabilizerscale   = 1.0,
            usebuffer         = True,
            )
        ),
    )


vmc_sections_keys = [
    'walkers','warmupsteps','blocks','steps',
    'substeps','timestep','checkpoint',
    'J0_warmupsteps','J0_blocks','J0_steps',
    'test_warmupsteps','test_blocks','test_steps',
    ]
vmc_sections_defaults = obj(
    v1 = obj(
        walkers          = 1,
        warmupsteps      = 50,
        blocks           = 800,
        steps            = 10,
        substeps         = 3,
        timestep         = 0.3,
        checkpoint       = -1,
        test_warmupsteps = 10,
        test_blocks      = 20,
        test_steps       =  4,
        J0_warmupsteps   = 200,
        J0_blocks        = 800,
        J0_steps         = 100,
        ),
    )



dmc_sections_keys = [
    'walkers','warmupsteps','blocks','steps',
    'timestep','checkpoint',
    'vmc_samples','vmc_samplesperthread',
    'vmc_walkers','vmc_warmupsteps','vmc_blocks','vmc_steps',
    'vmc_substeps','vmc_timestep','vmc_checkpoint',
    'eq_dmc','eq_warmupsteps','eq_blocks','eq_steps','eq_timestep','eq_checkpoint',
    'J0_warmupsteps','J0_blocks','J0_steps','J0_checkpoint',
    'test_warmupsteps','test_blocks','test_steps',
    'ntimesteps','timestep_factor',
    ]
dmc_sections_required = ['nlmove']



scf_workflow_keys = []
scf_input_defaults = obj(
    none    = obj(
        ),
    minimal = obj(
        identifier       = 'scf',
        input_type       = 'generic',
        nosym            = True,
        wf_collect       = True,
        use_folded       = True,
        nogamma          = True,
        ),
    v1 = obj(
        identifier       = 'scf',
        input_type       = 'generic',
        diagonalization  = 'david',
        electron_maxstep = 1000,
        conv_thr         = 1e-8,
        mixing_beta      = 0.2,
        occupations      = 'smearing',
        smearing         = 'fermi-dirac',
        degauss          = 0.0001,
        nosym            = True,
        wf_collect       = True,
        use_folded       = True,
        nogamma          = True,
        ),
    )

p2q_workflow_keys = []
p2q_input_defaults = obj(
    minimal = obj(
        identifier = 'p2q',
        write_psir = False,
        ),
    v1 = obj(
        identifier = 'p2q',
        write_psir = False,
        ),
    )

opt_workflow_keys = ['J2_prod','J3_prod','J_defaults']
fixed_defaults = obj(
    J2_prod    = False,
    J3_prod    = False,
    J_defaults = defaults_version,
    )
opt_input_defaults = obj(
    minimal = obj(
        identifier   = 'opt',
        input_type   = 'basic',
        **fixed_defaults
        ),
    v1 = obj(
        identifier   = 'opt',
        input_type   = 'basic',
        **fixed_defaults
        ),
    )

vmc_workflow_keys = [
    'J0_prod','J2_prod','J3_prod',
    'J0_test','J2_test','J3_test',
    ] 
fixed_defaults = obj(
    J0_prod = False,
    J2_prod = False,
    J3_prod = False,
    J0_test = False,
    J2_test = False,
    J3_test = False,
    )
vmc_input_defaults = obj(
    minimal = obj(
        identifier   = 'vmc',
        input_type   = 'basic',
        **fixed_defaults
        ),
    v1 = obj(
        identifier       = 'vmc',
        input_type       = 'basic',
        walkers          = 1,
        warmupsteps      = 50,
        blocks           = 800,
        steps            = 10,
        substeps         = 3,
        timestep         = 0.3,
        checkpoint       = -1,
        test_warmupsteps = 10,
        test_blocks      = 20,
        test_steps       =  4,
        J0_warmupsteps   = 200,
        J0_blocks        = 800,
        J0_steps         = 100,
        **fixed_defaults
        ),
    )

dmc_workflow_keys = [
    'J0_prod','J2_prod','J3_prod',
    'J0_test','J2_test','J3_test',
    ]
fixed_defaults = obj(
    J0_prod  = False,
    J2_prod  = False,
    J3_prod  = False,
    J0_test  = False,
    J2_test  = False,
    J3_test  = False,
    tmoves   = False,
    locality = False,
    )
dmc_input_defaults = obj(
    minimal = obj(
        identifier   = 'qmc',
        input_type   = 'basic',
        **fixed_defaults
        ),
    v1 = obj(
        identifier   = 'qmc',
        input_type   = 'basic',
        **fixed_defaults
        ),
    )












def resolve_deps(name,sims,deps,loc='resolve_deps'):
    deplist = []
    missing = []
    for depname,depquant in deps:
        if depname in sims:
            deplist.append((sims[depname],depquant))
        else:
            missing.append(depname)
        #end if
    #end for
    if len(missing)>0:
        keywords = []
        for m in missing:
            if len(m)>=3:
                keywords.append(m[0:3]+'_inputs')
            #end if
        #end for
        error('workflow cannot be run\nsimulation "{0}" depends on other simulations that have not been requested\nmissing simulations: {1}\nthe user needs to provide more detailed input\nthis issue can likely be fixed by providing the following keywords: {2}'.format(name,sorted(missing),sorted(set(keywords))))
    #end if
    return deplist
#end def resolve_deps









def process_jastrow(J,system):
    if isinstance(J,(tuple,list)):
        J = generate_jastrow(*J,system=system)
    #end if
    return J
#end def process_jastrow



def jastrow_factor(
    J1           = missing,
    J2           = missing,
    J3           = missing,
    system       = missing,
    J1_size      = missing,
    J1_rcut      = missing,
    J2_size      = missing,
    J2_rcut      = missing,
    J2_init      = missing,
    J3_isize     = missing,
    J3_esize     = missing,
    J3_rcut      = missing,
    J1_rcut_open = missing,
    J2_rcut_open = missing,
    defaults     = defaults_version,
    loc          = 'jastrow_factor',
    ):

    set_def_loc(jastrow_factor_defaults[defaults],loc)

    J1           = default('J1'          ,J1          )
    J2           = default('J2'          ,J2          )
    J3           = default('J3'          ,J3          )
    J1_size      = default('J1_size'     ,J1_size     )
    J1_rcut      = default('J1_rcut'     ,J1_rcut     )
    J2_size      = default('J2_size'     ,J2_size     )
    J2_rcut      = default('J2_rcut'     ,J2_rcut     )
    J2_init      = default('J2_init'     ,J2_init     )
    J3_isize     = default('J3_isize'    ,J3_isize    )
    J3_esize     = default('J3_esize'    ,J3_esize    )
    J3_rcut      = default('J3_rcut'     ,J3_rcut     )
    J1_rcut_open = default('J1_rcut_open',J1_rcut_open) 
    J2_rcut_open = default('J2_rcut_open',J2_rcut_open) 
    
    require('system',system)

    openbc = system.structure.is_open()

    J1 = process_jastrow(J1,system)
    J2 = process_jastrow(J2,system)
    J3 = process_jastrow(J3,system)

    if J1==True:
        if openbc and J1_rcut is None:
            J1_rcut = J1_rcut_open
        #end if
        J1 = generate_jastrow('J1','bspline',J1_size,J1_rcut,system=system)
    #end if
    if J2==True:
        if openbc and J2_rcut is None:
            J2_rcut = J2_rcut_open
        #end if
        J2 = generate_jastrow('J2','bspline',J2_size,J2_rcut,init=J2_init,system=system)
    #end if
    if J3==True:
        J3 = generate_jastrow('J3','polynomial',J3_esize,J3_isize,J3_rcut,system=system)
    #end if

    jastrows = []
    if J1!=False:
        jastrows.append(J1)
    #end if
    if J2!=False:
        jastrows.append(J2)
    #end if
    if J3!=False:
        jastrows.append(J3)
    #end if

    return jastrows
#end def jastrow_factor




def opt_sections(
    method              = missing,
    cost                = missing,
    cycles              = missing,
    var_cycles          = missing,
    opt_calcs           = missing,
    # linear/cslinear inputs
    blocks              = missing,
    warmupsteps         = missing,
    stepsbetweensamples = missing,
    timestep            = missing,
    samples             = missing,
    minwalkers          = missing,
    maxweight           = missing,
    usedrift            = missing,
    minmethod           = missing,
    beta                = missing,
    exp0                = missing,
    bigchange           = missing,
    alloweddifference   = missing,
    stepsize            = missing,
    stabilizerscale     = missing,
    nstabilizers        = missing,
    max_its             = missing,
    cgsteps             = missing,
    eigcg               = missing,
    walkers             = missing,
    nonlocalpp          = missing,
    usebuffer           = missing,
    gevmethod           = missing,
    steps               = missing,
    substeps            = missing, 
    stabilizermethod    = missing,
    cswarmupsteps       = missing,
    alpha_error         = missing,
    gevsplit            = missing,
    beta_error          = missing,
    defaults            = defaults_version,
    loc                 = 'opt_sections',
    ):

    if not missing(opt_calcs):
        return opt_calcs
    #end if

    set_def_loc(opt_sections_defaults[defaults],loc)

    method     = default('method'    ,method    )
    cost       = default('cost'      ,cost      )
    cycles     = default('cycles'    ,cycles    )
    var_cycles = default('var_cycles',var_cycles)

    methods = obj(linear=linear,cslinear=cslinear)
    if method not in methods:
        error('invalid optimization method requested\ninvalid method: {0}\nvalid options are: {1}'.format(method,sorted(methods.keys())),loc)
    #end if
    opt = methods[method]

    set_def_loc(opt_method_defaults[method][defaults],loc,strict=False)

    opt_inputs = obj()
    assign_default(opt_inputs,'blocks'             ,blocks             )
    assign_default(opt_inputs,'warmupsteps'        ,warmupsteps        )
    assign_default(opt_inputs,'stepsbetweensamples',stepsbetweensamples)
    assign_default(opt_inputs,'timestep'           ,timestep           )
    assign_default(opt_inputs,'samples'            ,samples            )
    assign_default(opt_inputs,'minwalkers'         ,minwalkers         )
    assign_default(opt_inputs,'maxweight'          ,maxweight          )
    assign_default(opt_inputs,'usedrift'           ,usedrift           )
    assign_default(opt_inputs,'minmethod'          ,minmethod          )
    assign_default(opt_inputs,'beta'               ,beta               )
    assign_default(opt_inputs,'exp0'               ,exp0               )
    assign_default(opt_inputs,'bigchange'          ,bigchange          )
    assign_default(opt_inputs,'alloweddifference'  ,alloweddifference  )
    assign_default(opt_inputs,'stepsize'           ,stepsize           )
    assign_default(opt_inputs,'stabilizerscale'    ,stabilizerscale    )
    assign_default(opt_inputs,'nstabilizers'       ,nstabilizers       )
    assign_default(opt_inputs,'max_its'            ,max_its            )
    assign_default(opt_inputs,'cgsteps'            ,cgsteps            )
    assign_default(opt_inputs,'eigcg'              ,eigcg              )
    assign_default(opt_inputs,'walkers'            ,walkers            )
    assign_default(opt_inputs,'nonlocalpp'         ,nonlocalpp         )
    assign_default(opt_inputs,'usebuffer'          ,usebuffer          )
    assign_default(opt_inputs,'gevmethod'          ,gevmethod          )
    assign_default(opt_inputs,'steps'              ,steps              )
    assign_default(opt_inputs,'substeps'           ,substeps           ) 
    assign_default(opt_inputs,'stabilizermethod'   ,stabilizermethod   )
    assign_default(opt_inputs,'cswarmupsteps'      ,cswarmupsteps      )
    assign_default(opt_inputs,'alpha_error'        ,alpha_error        )
    assign_default(opt_inputs,'gevsplit'           ,gevsplit           )
    assign_default(opt_inputs,'beta_error'         ,beta_error         )

    if cost=='variance':
        cost = (0.0,1.0,0.0)
    elif cost=='energy':
        cost = (1.0,0.0,0.0)
    elif isinstance(cost,(tuple,list)) and (len(cost)==2 or len(cost)==3):
        if len(cost)==2:
            cost = (cost[0],0.0,cost[1])
        #end if
    else:
        error('invalid optimization cost function encountered\ninvalid cost fuction: {0}\nvalid options are: variance, energy, (0.95,0.05), etc'.format(cost),loc)
    #end if
    opt_calcs = []
    if abs(cost[0])>1e-6:
        vmin_opt = opt(
            energy               = 0.0,
            unreweightedvariance = 1.0,
            reweightedvariance   = 0.0,
            **opt_inputs
            )
        opt_calcs.append(loop(max=var_cycles,qmc=vmin_opt))
    #end if
    cost_opt = opt(
        energy               = cost[0],
        unreweightedvariance = cost[1],
        reweightedvariance   = cost[2],
        **opt_inputs
        )
    opt_calcs.append(loop(max=cycles,qmc=cost_opt))
    return opt_calcs
#end def opt_sections



def vmc_sections(
    walkers          = missing,
    warmupsteps      = missing,
    blocks           = missing,
    steps            = missing,
    substeps         = missing,
    timestep         = missing,
    checkpoint       = missing,
    J0_warmupsteps   = missing,
    J0_blocks        = missing,
    J0_steps         = missing,
    test_warmupsteps = missing,
    test_blocks      = missing,
    test_steps       = missing,
    vmc_calcs        = missing,
    J0               = False,
    test             = False,
    defaults         = defaults_version,
    loc              = 'vmc_sections',
    ):

    if not missing(vmc_calcs):
        return vmc_calcs
    #end if

    set_def_loc(vmc_sections_defaults[defaults],loc)

    walkers          = default('walkers'         ,walkers         )
    warmupsteps      = default('warmupsteps'     ,warmupsteps     )
    blocks           = default('blocks'          ,blocks          )
    steps            = default('steps'           ,steps           )
    substeps         = default('substeps'        ,substeps        )
    timestep         = default('timestep'        ,timestep        )
    checkpoint       = default('checkpoint'      ,checkpoint      )
    J0_warmupsteps   = default('J0_warmupsteps'  ,J0_warmupsteps  )
    J0_blocks        = default('J0_blocks'       ,J0_blocks       )
    J0_steps         = default('J0_steps'        ,J0_steps        )
    test_warmupsteps = default('test_warmupsteps',test_warmupsteps)
    test_blocks      = default('test_blocks'     ,test_blocks     )
    test_steps       = default('test_steps'      ,test_steps      )
    
    if test:
        warmup = test_warmupsteps,
        blocks = test_blocks,
        steps  = test_steps,
    elif J0:
        warmup = J0_warmupsteps
        blocks = J0_blocks
        steps  = J0_steps
    else:
        warmup = warmupsteps
        blocks = blocks
        steps  = steps
    #end if
    vmc_calcs = [
        vmc(
            walkers     = walkers,
            warmupsteps = warmup,
            blocks      = blocks,
            steps       = steps,
            substeps    = substeps,
            timestep    = timestep,
            checkpoint  = checkpoint,
            )
        ]
    return vmc_calcs
#end def vmc_sections



def dmc_sections(**kwargs):
    if 'dmc_calcs' in kwargs:
        return kwargs['dmc_calcs']
    #end if
    loc      = kwargs.pop('loc','dmc_sections')
    defaults = kwargs.pop('defaults',defaults_version)
    J0       = kwargs.pop('J0',False)
    test     = kwargs.pop('test',False)
    kw = extract_kwargs(
        kwargs          = kwargs,
        required        = dmc_sections_required,
        optional        = dmc_sections_options,
        defaults        = defaults,
        default_sources = vmc_defaults,
        require_empty   = True,
        encapsulate     = False,
        )
    if 'vmc_samples' not in kw and 'vmc_samplesperthread' not in kw:
        error('vmc samples (dmc walkers) not specified\nplease provide one of the following keywords: vmc_samples, vmc_samplesperthread',loc)
    #end if
    vsec = vmc(
        walkers     = kw.vmc_walkers,
        warmupsteps = kw.vmc_warmupsteps,
        blocks      = kw.vmc_blocks,
        steps       = kw.vmc_steps,
        substeps    = kw.vmc_substeps,
        timestep    = kw.vmc_timestep,
        checkpoint  = kw.vmc_checkpoint,
        )
    if 'vmc_samples' in kw:
        vsec.samples = kw.vmc_samples
    elif 'vmc_samplesperthread' in kw:
        vsec.samplesperthread = kw.vmc_samplesperthread
    #end if
    dmc_calcs = [vsec]
    if kw.eq_dmc:
        deqsec = dmc(
            walkers 
            )
    #end if

#end def dmc_sections






qmcpack_chain_required = ['system','sim_list','dft_pseudos','qmc_pseudos']
qmcpack_chain_defaults = obj(
    scf            = False,
    p2q            = False,
    opt            = False,
    vmc            = False,
    dmc            = False,
    scf_inputs     = None,
    p2q_inputs     = None,
    opt_inputs     = None,
    vmc_inputs     = None,
    dmc_inputs     = None,
    scf_defaults   = defaults_version,
    p2q_defaults   = defaults_version,
    opt_defaults   = defaults_version,
    vmc_defaults   = defaults_version,
    dmc_defaults   = defaults_version,
    orb_source     = None,
    J2_source      = None,
    J3_source      = None,
    processed      = False,
    )


def process_qmcpack_chain_kwargs(
    system        = missing,
    sim_list      = missing,
    dft_pseudos   = missing,
    qmc_pseudos   = missing,
    scf           = missing,
    p2q           = missing,
    opt           = missing,
    vmc           = missing,
    dmc           = missing,
    scf_inputs    = missing,
    p2q_inputs    = missing,
    opt_inputs    = missing,
    vmc_inputs    = missing,
    dmc_inputs    = missing,
    scf_defaults  = missing,
    p2q_defaults  = missing,
    opt_defaults  = missing,
    vmc_defaults  = missing,
    dmc_defaults  = missing,
    orb_source    = missing,
    J2_source     = missing,
    J3_source     = missing,
    defaults      = missing,
    loc           = 'process_qmcpack_chain_kwargs',
    processed     = False,
    **invalid_kwargs
    ):

    prevent_invalid_input(invalid_kwargs,loc)

    if missing(defaults):
        defaults = qmcpack_chain_defaults,
    else:
        defaults.set_optional(**qmcpack_chain_defaults)
    #end if

    set_def_loc(defaults,loc)

    kw = obj()

    assign_require(kw,'system'     ,system     )
    assign_require(kw,'sim_list'   ,sim_list   )
    assign_require(kw,'dft_pseudos',dft_pseudos)

    assign_default(kw,'scf'         ,scf         )
    assign_default(kw,'p2q'         ,p2q         )
    assign_default(kw,'opt'         ,opt         )
    assign_default(kw,'vmc'         ,vmc         )
    assign_default(kw,'dmc'         ,dmc         )
    assign_default(kw,'scf_inputs'  ,scf_inputs  )
    assign_default(kw,'p2q_inputs'  ,p2q_inputs  )
    assign_default(kw,'opt_inputs'  ,opt_inputs  )
    assign_default(kw,'vmc_inputs'  ,vmc_inputs  )
    assign_default(kw,'dmc_inputs'  ,dmc_inputs  )
    assign_default(kw,'scf_defaults',scf_defaults)
    assign_default(kw,'p2q_defaults',p2q_defaults)
    assign_default(kw,'opt_defaults',opt_defaults)
    assign_default(kw,'vmc_defaults',vmc_defaults)
    assign_default(kw,'dmc_defaults',dmc_defaults)
    assign_default(kw,'orb_source'  ,orb_source  )
    assign_default(kw,'J2_source'   ,J2_source   )
    assign_default(kw,'J3_source'   ,J3_source   )

    kw.scf |= kw.scf_inputs!=None
    kw.p2q |= kw.p2q_inputs!=None
    kw.opt |= kw.opt_inputs!=None
    kw.vmc |= kw.vmc_inputs!=None
    kw.dmc |= kw.dmc_inputs!=None

    if kw.opt or kw.vmc or kw.dmc:
        assign_require(kw,'qmc_pseudos',qmc_pseudos)
    #end if

    
    if kw.scf:
        # kw.scf_inputs contains inputs to generate_pwscf after this
        set_loc(loc+' scf_inputs')
        kw.scf_inputs = obj(**kw.scf_inputs)
        assign_defaults(kw.scf_inputs,scf_input_defaults[kw.scf_defaults])
        kw.scf_inputs.set(
            system  = kw.system,
            pseudos = kw.dft_pseudos,
            )
        kw.scf_workflow = extract_keywords(kw.scf_inputs,scf_workflow_keys)
    #end if
    if kw.p2q:
        # kw.p2q_inputs contains inputs to generate_pw2qmcpack after this
        set_loc(loc+' p2q_inputs')
        kw.p2q_inputs = obj(**kw.p2q_inputs)
        assign_defaults(kw.p2q_inputs,p2q_input_defaults[kw.p2q_defaults])
        kw.p2q_workflow = extract_keywords(kw.p2q_inputs,p2q_workflow_keys)
    #end if
    if kw.opt:
        set_loc(loc+' opt_inputs')
        kw.opt_inputs = obj(**kw.opt_inputs)
        assign_defaults(kw.opt_inputs,opt_input_defaults[kw.opt_defaults])
        kw.opt_inputs.set(
            system  = kw.system,
            pseudos = kw.qmc_pseudos,
            )
        kw.opt_workflow = extract_keywords(kw.opt_inputs,opt_workflow_keys)

        set_loc(loc+'opt_inputs jastrows')
        #assign_defaults(kw.opt_inputs,jastrow_factor_defaults[kw.opt_workflow.J_defaults])
        jkw = extract_keywords(kw.opt_inputs,jastrow_factor_keys,optional=True)
        jkw.system = kw.system
        jkw.defaults = kw.opt_workflow.J_defaults
        j2kw = jkw.copy()
        j2kw.set(J1=1,J2=1,J3=0)
        j3kw = jkw.copy()
        j3kw.set(J1=1,J2=1,J3=1)
        kw.J2_inputs = j2kw
        kw.J3_inputs = j3kw

        set_loc(loc+'opt_inputs opt_methods')
        kw.opt_sec_inputs = extract_keywords(kw.opt_inputs,opt_sections_keys,optional=True)
    #end if
    if kw.vmc:
        set_loc(loc+' vmc_inputs')
        kw.vmc_inputs = obj(**kw.vmc_inputs)
        assign_defaults(kw.vmc_inputs,vmc_input_defaults[kw.vmc_defaults])
        kw.vmc_inputs.set(
            system  = kw.system,
            pseudos = kw.qmc_pseudos,
            )
        kw.vmc_workflow = extract_keywords(kw.vmc_inputs,vmc_workflow_keys)

        kw.vmc_sec_inputs = extract_keywords(kw.vmc_inputs,vmc_sections_keys,optional=True)
    #end if
    if kw.dmc:
        set_loc(loc+' dmc_inputs')
        kw.dmc_inputs = obj(**kw.dmc_inputs)
        assign_defaults(kw.dmc_inputs,dmc_input_defaults[kw.dmc_defaults])
        kw.dmc_inputs.set(
            system  = kw.system,
            pseudos = kw.qmc_pseudos,
            )
        kw.dmc_workflow = extract_keywords(kw.dmc_inputs,dmc_workflow_keys)

        kw.dmc_sec_inputs = extract_keywords(kw.dmc_inputs,dmc_sections_keys,optional=True)
    #end if

    del kw.scf_defaults
    del kw.p2q_defaults
    del kw.opt_defaults
    del kw.vmc_defaults
    del kw.dmc_defaults

    kw.processed = True

    return kw
#end def process_qmcpack_chain_kwargs


def qmcpack_chain(**kwargs):
    loc       = kwargs.pop('loc','qmcpack_chain')
    processed = kwargs.pop('processed',False)
    if processed:
        kw = obj(**kwargs)
    else:
        kw = process_qmcpack_chain_kwargs(loc=loc,**kwargs)
    #end if
    basepath = kw.basepath
    sim_list = kw.sim_list
    sims = obj()

    if kw.orb_source!=None:
        sims.p2q = kw.orb_source
    else:
        if kw.scf:
            scf = generate_pwscf(
                path = os.path.join(basepath,'scf'),
                **kw.scf_inputs
                )
            sims.scf = scf
        #end if

        if kw.p2q:
            deps = resolve_deps('p2q',sims,[('scf','orbitals')],loc)
            p2q = generate_pw2qmcpack(
                path         = os.path.join(basepath,'scf'),
                dependencies = deps,
                **kw.p2q_inputs
                )
            sims.p2q = p2q
        #end if
    #end if
        
    orbdep = [('p2q','orbitals')]
    J2dep  = orbdep + [('optJ2','jastrow')]
    J3dep  = orbdep + [('optJ3','jastrow')]

    if kw.opt:
        if kw.opt_workflow.J2_prod and kw.J2_source is None:
            deps = resolve_deps('optJ2',sims,orbdep,loc)
            optJ2 = generate_qmcpack(
                path         = os.path.join(basepath,'optJ2'),
                jastrows     = jastrow_factor(**kw.J2_inputs),
                calculations = opt_sections(**kw.opt_sec_inputs),
                dependencies = deps,
                **kw.opt_inputs
                )
            sims.optJ2 = optJ2
        #end if
        if kw.opt_workflow.J3_prod and kw.J3_source is None:
            deps = resolve_deps('optJ3',sims,J2dep,loc)
            optJ3 = generate_qmcpack(
                path         = os.path.join(basepath,'optJ3'),
                jastrows     = jastrow_factor(**kw.J3_inputs),
                calculations = opt_sections(**kw.opt_sec_inputs),
                dependencies = deps,
                **kw.opt_inputs
                )
            sims.optJ3 = optJ3
        #end if
    #end if
    if kw.J2_source!=None:
        sims.optJ2 = kw.J2_source
    #end if
    if kw.J3_source!=None:
        sims.optJ3 = kw.J3_source
    #end if

    if kw.vmc:
        if kw.vmc_workflow.J0_test:
            deps = resolve_deps('vmcJ0_test',sims,orbdep,loc)
            vmcJ0_test = generate_qmcpack(
                path         = os.path.join(basepath,'vmcJ0_test'),
                jastrows     = [],
                calculations = vmc_sections(test=1,J0=1,**kw.vmc_sec_inputs),
                dependencies = deps,
                **kw.vmc_inputs
                )
            sims.vmcJ0_test = vmcJ0_test
        #end if
        if kw.vmc_workflow.J0_prod:
            deps = resolve_deps('vmcJ0',sims,orbdep,loc)
            vmcJ0 = generate_qmcpack(
                path         = os.path.join(basepath,'vmcJ0'),
                jastrows     = [],
                calculations = vmc_sections(J0=1,**kw.vmc_sec_inputs),
                dependencies = deps,
                **kw.vmc_inputs
                )
            sims.vmcJ0 = vmcJ0
        #end if
        if kw.vmc_workflow.J2_test:
            deps = resolve_deps('vmcJ2_test',sims,J2dep,loc)
            vmcJ2_test = generate_qmcpack(
                path         = os.path.join(basepath,'vmcJ2_test'),
                jastrows     = [],
                calculations = vmc_sections(test=1,**kw.vmc_sec_inputs),
                dependencies = deps,
                **kw.vmc_inputs
                )
            sims.vmcJ2_test = vmcJ2_test
        #end if
        if kw.vmc_workflow.J2_prod:
            deps = resolve_deps('vmcJ2',sims,J2dep,loc)
            vmcJ2 = generate_qmcpack(
                path         = os.path.join(basepath,'vmcJ2'),
                jastrows     = [],
                calculations = vmc_sections(**kw.vmc_sec_inputs),
                dependencies = deps,
                **kw.vmc_inputs
                )
            sims.vmcJ2 = vmcJ2
        #end if
        if kw.vmc_workflow.J3_test:
            deps = resolve_deps('vmcJ3_test',sims,J3dep,loc)
            vmcJ3_test = generate_qmcpack(
                path         = os.path.join(basepath,'vmcJ3_test'),
                jastrows     = [],
                calculations = vmc_sections(test=1,**kw.vmc_sec_inputs),
                dependencies = deps,
                **kw.vmc_inputs
                )
            sims.vmcJ3_test = vmcJ3_test
        #end if
        if kw.vmc_workflow.J3_prod:
            deps = resolve_deps('vmcJ3',sims,J2dep,loc)
            vmcJ3 = generate_qmcpack(
                path         = os.path.join(basepath,'vmcJ3'),
                jastrows     = [],
                calculations = vmc_sections(**kw.vmc_sec_inputs),
                dependencies = deps,
                **kw.vmc_inputs
                )
            sims.vmcJ3 = vmcJ3
        #end if
    #end if

    if kw.dmc:
        nonloc_labels = {None:'',True:'_tm',False:'_la'}
        nonlocalmoves_default = None
        if system.is_pseudized():
            nonlocalmoves_default = True
        #end if
        nloc_moves = []
        if kw.dmc_workflow.tmoves:
            nloc_moves.append(True)
        #end if
        if kw.dmc_workflow.locality:
            nloc_moves.append(False)
        #end if
        if not kw.dmc_workflow.tmoves and not kw.dmc_workflow.locality:
            nloc_moves.append(nonlocal_moves_default)
        #end if
        for nlmove in nloc_moves:
            nll = nonloc_labels[nlmove]
            if kw.dmc_workflow.J0_test:
                label = 'dmcJ0'+nll+'_test'
                deps = resolve_deps(label,sims,orbdep,loc)
                dmcJ0_test = generate_qmcpack(
                    path         = os.path.join(basepath,label),
                    jastrows     = [],
                    calculations = dmc_sections(nlmove=nlmove,test=1,J0=1,**kw.dmc_sec_inputs),
                    dependencies = deps,
                    **kw.dmc_inputs
                    )
                sims[label] = dmcJ0_test
            #end if
            if kw.dmc_workflow.J0_prod:
                label = 'dmcJ0'+nll
                deps = resolve_deps(label,sims,orbdep,loc)
                dmcJ0 = generate_qmcpack(
                    path         = os.path.join(basepath,label),
                    jastrows     = [],
                    calculations = dmc_sections(nlmove=nlmove,J0=1,**kw.dmc_sec_inputs),
                    dependencies = deps,
                    **kw.dmc_inputs
                    )
                sims[label] = dmcJ0
            #end if
            if kw.dmc_workflow.J2_test:
                label = 'dmcJ2'+nll+'_test'
                deps = resolve_deps(label,sims,J2dep,loc)
                dmcJ2_test = generate_qmcpack(
                    path         = os.path.join(basepath,label),
                    jastrows     = [],
                    calculations = dmc_sections(nlmove=nlmove,test=1,**kw.dmc_sec_inputs),
                    dependencies = deps,
                    **kw.dmc_inputs
                    )
                sims[label] = dmcJ2_test
            #end if
            if kw.dmc_workflow.J2_prod:
                label = 'dmcJ2'+nll
                deps = resolve_deps(label,sims,J2dep,loc)
                dmcJ2 = generate_qmcpack(
                    path         = os.path.join(basepath,label),
                    jastrows     = [],
                    calculations = dmc_sections(nlmove=nlmove,**kw.dmc_sec_inputs),
                    dependencies = deps,
                    **kw.dmc_inputs
                    )
                sims[label] = dmcJ2
            #end if
            if kw.dmc_workflow.J3_test:
                label = 'dmcJ3'+nll+'_test'
                deps = resolve_deps(label,sims,J3dep,loc)
                dmcJ3_test = generate_qmcpack(
                    path         = os.path.join(basepath,label),
                    jastrows     = [],
                    calculations = dmc_sections(nlmove=nlmove,test=1,**kw.dmc_sec_inputs),
                    dependencies = deps,
                    **kw.dmc_inputs
                    )
                sims[label] = dmcJ3_test
            #end if
            if kw.dmc_workflow.J3_prod:
                label = 'dmcJ3'+nll
                deps = resolve_deps(label,sims,J2dep,loc)
                dmcJ3 = generate_qmcpack(
                    path         = os.path.join(basepath,label),
                    jastrows     = [],
                    calculations = dmc_sections(nlmove=nlmove,**kw.dmc_sec_inputs),
                    dependencies = deps,
                    **kw.dmc_inputs
                    )
                sims[label] = dmcJ3
            #end if
        #end if
    #end if

    sim_list.extend(sims.list())

    return sims
#end def qmcpack_chain


ecut_scan_chain_defaults = obj(
    scf = True,
    p2q = True,
    opt = True,
    vmc = True,
    )
def ecut_scan(
    ecuts        = missing,
    basepath     = missing,
    dirname      = 'ecut_scan',
    same_jastrow = True,
    ecut_jastrow = None,
    **kwargs
    ):

    loc = 'ecut_scan'

    set_def_loc(obj(),loc)

    require('ecuts'   ,ecuts   )
    require('basepath',basepath)

    ecuts = list(ecuts)

    qckw = process_qmcpack_chain_kwargs(
        defaults = ecut_scan_chain_defaults,
        loc      = loc,
        **kwargs
        )

    if not qckw.scf:
        error('cannot perform ecut scan, no inputs given for scf calculations',loc)
    #end if

    if same_jastrow:
        if ecut_jastrow is None:
            ecut_jastrow = max(ecuts)
        #end if
        found = False
        n=0
        for ecut in ecuts:
            if abs(ecut_jastrow-ecut)<1e-2:
                found = True
                break
            #end if
            n+=1
        #end for
        if not found:
            error('could not find ecut for fixed jastrow in list\necut searched for: {0}\necut list: {1}'.format(ecut_jastrow,ecuts),loc)
        #end if
        ecuts.pop(n)
        ecuts = [ecut_jastrow]+ecuts
    #end if
    J2_source = None
    J3_source = None
    sims = obj()
    for ecut in ecuts:
        qckw.basepath = os.path.join(basepath,dirname,'ecut_{0}'.format(ecut))
        qckw.scf_inputs.ecutwfc = ecut
        if J2_source is not None:
            qckw.J2_source = J2_source
        #end if
        if J3_source is not None:
            qckw.J3_source = J3_source
        #end if
        qcsims = qmcpack_chain(**qckw)
        if same_jastrow:
            J2_source = qcsims.get_optional('optJ2',None)
            J3_source = qcsims.get_optional('optJ3',None)
        #end if
        sims[ecut] = qcsims
    #end for
    return sims
#end def ecut_scan



def system_scan(
    basepath     = missing,
    dirname      = 'system_scan',
    systems      = missing,
    sysdirs      = missing,
    syskeys      = None,
    same_jastrow = False,
    jastrow_key  = missing,
    loc          = 'system_scan',
    **kwargs
    ):
    set_loc(loc)

    require('basepath',basepath)
    require('systems' ,systems )
    require('sysdirs' ,sysdirs )

    if syskeys is None:
        syskeys = sysdirs
    #end if

    if len(systems)==0:
        error('no systems provided',loc)
    #end if
    if len(sysdirs)!=len(systems):
        error('must provide one directory per system via sysdirs keyword\nnumber of directories provided: {0}\nnumber of systems: {1}'.format(len(sysdirs),len(systems)),loc)
    #end if
    if len(syskeys)!=len(systems):
        error('must provide one key per system via syskeys keyword\nnumber of keys provided: {0}\nnumber of systems: {1}'.format(len(syskeys),len(systems)),loc)
    #end if

    if same_jastrow:
        if missing(jastrow_key):
            error('requested same jastrow across scan but no system key was provided via jastrow_key keyword',loc)
        elif jastrow_key not in set(syskeys):
            error('key used to identify jastrow for use across scan was not found\njastrow key provided: {0}\nsystem keys present: {1}'.format(jastrow_key,sorted(system_keys)),loc)
        #end if
        sys = obj()
        for n in xrange(len(systems)):
            sys[syskeys[n]] = systems[n],sysdirs[n]
        #end for
        key_system,key_sysdir = sys[jastrow_key]
        del sys[jastrow_key]
        systems = [key_system]
        sysdirs = [key_sysdir]
        syskeys = [jastrow_key]
        for syskey in sys.keys():
            system,sydir = sys[syskey]
            systems.append(system)
            sysdirs.append(sysdir)
            syskeys.append(syskey)
        #end for
    #end if

    J2_source = None
    J3_source = None
    sims = obj()
    for n in xrange(len(systems)):
        qckw = process_qmcpack_chain_kwargs(
            defaults = qmcpack_chain_defaults,
            system   = systems[n],
            loc      = loc,
            **kwargs
            )
        qckw.basepath = os.path.join(basepath,dirname,sysdirs[n])
        if J2_source is not None:
            qckw.J2_source = J2_source
        #end if
        if J3_source is not None:
            qckw.J3_source = J3_source
        #end if
        qcsims = qmcpack_chain(**qckw)
        if same_jastrow:
            J2_source = qcsims.get_optional('optJ2',None)
            J3_source = qcsims.get_optional('optJ3',None)
        #end if
        sims[syskeys[n]] = qcsims
    #end for
    return sims
#end def system_scan



def system_parameter_scan(
    basepath = missing,
    dirname  = 'system_param_scan',
    sysfunc  = missing,
    variable = missing,
    values   = missing,
    fixed    = None,
    loc      = 'system_parameter_scan',
    **kwargs
    ):

    set_loc(loc)

    require('basepath',basepath)
    require('sysfunc' ,sysfunc )
    require('variable',variable)
    require('values'  ,values  )

    systems = []
    sysdirs = []
    syskeys = []
    for v in values:
        params = obj()
        params[variable] = v
        if fixed!=None:
            params.set(**fixed)
        #end if
        system = sysfunc(**params)
        if isinstance(v,list):
            vkey = tuple(v)
        elif isinstance(v,ndarray):
            vkey = tuple(v.ravel())
        else:
            vkey = v
        #end if
        if not hashable(vkey):
            error('inputted system generation variable value is not hashable\nvalue provided: {0}\nvalue type: {1}\nplease restrict system generation variables to basic types such as str,int,float,tuple and combinations of these'.format(v,v.__class__.__name__),loc)
        #end if
        if isinstance(vkey,(int,float,str)):
            vstr = str(vkey)
        elif isinstance(vkey,tuple):
            vstr = str(vkey).replace('(','').replace(')','').replace(' ','').replace(',','_')
        else:
            error('cannot convert system generation variable value into a directory name\nvalue provided: {0}\nvalue type: {1}\nplease restrict system generation variables to basic types such as str,int,float,tuple and combinations of these'.format(v,v.__class__.__name__),loc)
        #end if
        sysdir = '{0}_{1}'.format(variable,vstr)
        systems.append(system)
        sysdirs.append(sysdir)
        syskeys.append(vkey)
    #end for

    sp_sims = system_scan(
        basepath = basepath,
        dirname  = dirname,
        systems  = systems,
        sysdirs  = sysdirs,
        syskeys  = syskeys,
        **kwargs
        )

    return sp_sims
#end def system_parameter_scan





if __name__=='__main__':
    print 'simple driver for qmcpack_workflows functions'

    tests = obj(
        opt_sections = 1,
        )

    if tests.opt_sections:
        print
        print 'opt_sections()'
        opt_calcs = opt_sections()
        for calc in opt_calcs:
            print calc
        #end for

        print
        print "opt_sections(defaults=None)"
        opt_calcs = opt_sections(defaults=None)
        for calc in opt_calcs:
            print calc
        #end for

        print
        print "opt_sections(defaults='yl')"
        opt_calcs = opt_sections(defaults='yl')
        for calc in opt_calcs:
            print calc
        #end for

        print
        print "opt_sections(cost='energy')"
        opt_calcs = opt_sections(cost='energy')
        for calc in opt_calcs:
            print calc
        #end for

        print
        print "opt_sections(cost=(0.95,0.05))"
        opt_calcs = opt_sections(cost=(0.95,0.05))
        for calc in opt_calcs:
            print calc
        #end for

        print
        print "opt_sections(cost=(0.90,0.03,0.07),defaults=None)"
        opt_calcs = opt_sections(cost=(0.90,0.03,0.07),defaults=None)
        for calc in opt_calcs:
            print calc
        #end for

        print
        print "opt_sections(cost='energy',cycles=20,var_cycles=10,samples=1000000,defaults=None)"
        opt_calcs = opt_sections(cost='energy',cycles=20,var_cycles=10,samples=1000000,defaults=None)
        for calc in opt_calcs:
            print calc
        #end for

        #print
        #print 'fail test'
        #opt_sections(method='my_opt')
        #opt_sections(defaults='my_defaults')
        #opt_sections(bad_key='this')
        #opt_sections(cost=[0,0,0,0])
    #end if


#end if