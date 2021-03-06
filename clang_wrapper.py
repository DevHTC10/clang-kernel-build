#!/usr/bin/env python
from collections import defaultdict
import optparse
import os
import subprocess
import sys
import time

WORLD_PATH = os.path.dirname(os.path.abspath(__file__))

COMPILER_PATH = {'gcc': 'gcc',
  #'clang': WORLD_PATH + '/third_party/llvm-build/Release+Asserts/bin/clang'
  'clang': '/home/glider/src/llvm/llvm_cmake_build/bin/clang',
}

FILTER = {'gcc': ['-Qunused-arguments', '-no-integrated-as', '-mno-global-merge',
  '-Wdate-time', '-Wno-unknown-warning-option', '-Wno-initializer-overrides', '-Wno-tautological-compare',
  '-Wincompatible-pointer-types', '-Wno-gnu', '-Wno-format-invalid-specifier',
  '-Werror=date-time', '-Werror=incompatible-pointer-types',
],'clang': []}
SOURCE = 'source'
WRAPPER_LOG = WORLD_PATH + '/wrapper.log'
LOG = sys.stderr
LOG_OPTIONS = {'time': True, 'argv': True}

def compiler(flags):
  path = 'clang'
  return path  # no need to use GCC for now
  if SOURCE in flags:
    source = flags[SOURCE]
    #print >>LOG, source
    # kernel/* ok
    # kernel/[st] broken
    # kernel/[kmpstuw] broken
    # kernel/[abckmpstuw] broken
    # kernel/[abcdefgkmpstuw] ok
    # kernel/[defgkmpstuw] ok
    # kernel/[defgkm] ok
    # kernel/[defg] ok
    # kernel/[de] broken
    # kernel/[fg] ok
    # kernel/[f] broken
    # kernel/[g] ok -- that's kernel/groups.h
    if source.startswith('kernel/'):
      pieces = source.split('/')
      if pieces[1][0] in ['g']:
        path = 'gcc'
    #print >>LOG, path
  return path

def filter_args(argv, cname):
  new_argv = []
  for arg in argv:
    if arg not in FILTER[cname]:
      new_argv.append(arg)
  return new_argv

def want_msan_for_file(source):
  starts = ['lib/r', 'lib/t', 'lib/g']
  # Whacking the known reports.
  starts += ['kernel/time/hrtimer.c']
  starts += ['fs/proc/proc_sysctl.c', 'arch/x86/entry/vdso/vdso32-setup.c']
  starts += ['fs/proc/']
  starts += ['block/blk-ioc.c']
  starts += ['kernel/irq/irqdesc.c']
  starts += ['kernel/irq/proc.c']
  starts += ['mm/vmalloc.c']
  starts += ['kernel/exit.c', 'kernel/kmod.c', 'lib/kobject_uevent.c']
  starts += ['drivers/base/']
  ### hangs on boot
  ### starts += ['kernel/sched']
  ### starts += ['kernel/sched/fair.c']
  ### # lib/idr.c initializes memory allocated in fs/proc
  ### ['arch/x86/mm/ioremap.c', 'lib/idr.c']
  ### oopsing at boot time
  ###starts += ['arch/x86/kernel/apic/apic.c']
  ###starts += ['lib/k']
  if source.endswith('test_kmsan.c'):
    return True
  for i in starts:
    if source.startswith(i):
      return True
  return False


def msan_argv(flags, argv):
  source = flags[SOURCE]
  argv += ['-Wno-address-of-packed-member']
  if want_msan_for_file(source):
    argv += ['-fsanitize=memory', '-mllvm', '-msan-kernel=1', '-mllvm', '-msan-keep-going=1']
  #, '-fsanitize-memory-track-origins=2']
  return argv

def compiler_argv(flags, argv):
  cname = compiler(flags)
  new_argv = [COMPILER_PATH[cname]] + filter_args(argv, cname)
  if os.getenv('USE_MSAN'):
    new_argv = msan_argv(flags, new_argv)
  return new_argv

def make_flags(argv):
  flags = defaultdict(str)
  argv = argv[1:]
  for arg in argv:
    if arg.endswith('.c'):
      flags[SOURCE] = arg
  return flags, argv

def main(argv):
  global LOG
  LOG = file(WRAPPER_LOG, 'a+')
  if 'argv' in LOG_OPTIONS:
    print >>LOG, ' '.join(argv)
  flags, argv = make_flags(argv)
  new_argv = compiler_argv(flags, argv)
  #print >>LOG, ' '.join(new_argv)
  start_time = time.time()
  ret = subprocess.call(new_argv)
  end_time = time.time()
  if 'time' in LOG_OPTIONS:
    print >> LOG, 'Time elapsed: {:.3f} seconds'.format(end_time - start_time)
  LOG.close()
  return ret


if __name__ == '__main__':
  sys.exit(main(sys.argv))
