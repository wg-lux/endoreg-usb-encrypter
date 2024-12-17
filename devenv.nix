{ pkgs, lib, config, inputs, ... }:
let
  buildInputs = with pkgs; [
    python311Full
    # cudaPackages.cuda_cudart
    # cudaPackages.cudnn
    stdenv.cc.cc
  ];

  sops-nix = inputs.sops-nix;

in 
{

  # A dotenv file was found, while dotenv integration is currently not enabled.
  dotenv.enable = false;
  dotenv.disableHint = true;


  packages = with pkgs; [
    stdenv.cc.cc
    parted
    cryptsetup
    lsof
    e2fsprogs
  ];
  

  env = {
    LD_LIBRARY_PATH = "${
      with pkgs;
      lib.makeLibraryPath buildInputs
    }:/run/opengl-driver/lib:/run/opengl-driver-32/lib";

  };

  languages.python = {
    enable = true;
    uv = {
      enable = true;
      sync.enable = true;
    };
  };

  scripts.hello.exec = "${pkgs.uv}/bin/uv run python hello.py";
  scripts.gpu-check.exec = "${pkgs.uv}/bin/uv run python gpu_check.py";
  scripts.env-setup.exec = ''
    export LD_LIBRARY_PATH="${
      with pkgs;
      lib.makeLibraryPath buildInputs
    }:/run/opengl-driver/lib:/run/opengl-driver-32/lib"
  '';


  


  tasks = {};

  processes = {
  };

  enterShell = ''
    . .devenv/state/venv/bin/activate
    hello
  '';
}
