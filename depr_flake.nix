{
  description = "Flake for the Django based `endoreg-usb-encrypter`application";

  nixConfig = {
    substituters = [
        "https://cache.nixos.org"
      ];
    trusted-public-keys = [
        "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY="
      ];
    extra-substituters = "https://cache.nixos.org https://nix-community.cachix.org";
    extra-trusted-public-keys = "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY= nix-community.cachix.org-1:mB9FSh9qf2dCimDSUo8Zy7bkq5CX+/rkCWyvRCYg3Fs=";
  };

  inputs = {
    poetry2nix.url = "github:nix-community/poetry2nix";
    poetry2nix.inputs.nixpkgs.follows = "nixpkgs";


    cachix = {
      url = "github:cachix/cachix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { nixpkgs, poetry2nix, ... } @ inputs: 
  let 
    system = "x86_64-linux";
    self = inputs.self;
    version = "0.1.${pkgs.lib.substring 0 8 inputs.self.lastModifiedDate}.${inputs.self.shortRev or "dirty"}";
    python-version = "311";
    cachix = inputs.cachix;

    pkgs = import nixpkgs {
      inherit system;
      config = {
        allowUnfree = true;
      };
    };

    lib = pkgs.lib;

    pypkgs-build-requirements = {
      gender-guesser = [ "setuptools" ];
      conllu = [ "setuptools" ];
      janome = [ "setuptools" ];
      pptree = [ "setuptools" ];
      wikipedia-api = [ "setuptools" ];
      django-flat-theme = [ "setuptools" ];
      django-flat-responsive = [ "setuptools" ];
      pypdfium2 = [ "setuptools" ];
      logging = [ "setuptools" ];
    };

    poetry2nix = inputs.poetry2nix.lib.mkPoetry2Nix { inherit pkgs;};

    p2n-overrides = poetry2nix.defaultPoetryOverrides.extend (final: prev:
      builtins.mapAttrs (package: build-requirements:
        (builtins.getAttr package prev).overridePythonAttrs (old: {
          buildInputs = (old.buildInputs or [ ]) ++ (
            builtins.map (pkg:
              if builtins.isString pkg then builtins.getAttr pkg prev else pkg
            ) build-requirements
          );
        })
      ) pypkgs-build-requirements
    );

    poetryApp = poetry2nix.mkPoetryApplication {
      projectDir = ./.;
      src = lib.cleanSource ./.;
      python = pkgs."python${python-version}";
      overrides = p2n-overrides;
      preferWheels = true; # some packages, e.g. transformers break if false
      propagatedBuildInputs =  with pkgs."python${python-version}Packages"; [
        
      ];
      nativeBuildInputs = with pkgs."python${python-version}Packages"; [
        pip
        setuptools
      ];
      buildInputs = with pkgs; [
        poetry
        python311Packages.venvShellHook
        parted
        cryptsetup
        openssl
        lsof
        e2fsprogs
      ];

      venvDir = ".venv";
    };

    poetryEnv = poetry2nix.mkPoetryEnv {
      projectDir = ./.;
      python = pkgs."python${python-version}";
      extraPackages = (ps: [
        ps.pip
      ]);
      overrides = p2n-overrides;
      editablePackageSources = {};
      preferWheels = true;
    };
    
  in
  {

    packages.x86_64-linux.poetryApp = poetryApp;
    packages.x86_64-linux.default = poetryApp;
    
    apps.x86_64-linux.encrypter = {
      type = "app";
      program = "${poetryApp}/bin/encrypt-usb";
    };

    apps.x86_64-linux.default = self.apps.x86_64-linux.encrypter;
  
    devShells.x86_64-linux.default = pkgs.mkShell {
      buildInputs = [
        pkgs.poetry
        poetryEnv
        pkgs.python311Packages.numpy
        pkgs.python311Packages.venvShellHook
        pkgs.parted
        pkgs.cryptsetup
        pkgs.openssl
        pkgs.lsof
      ];
      venvDir = ".venv";
    };

    nixosModules = {
      encrypter = { config, pkgs, lib, ...}: 
        let
          mkOption = lib.mkOption;
        in
      {
        
        options.services.usb-encrypter = {

          enable = mkOption {
            default = true;
            description = "Enable the USB encrypter service";
            type = lib.types.bool;
          };

          user = mkOption {
            default = "root";
            description = "The user to run the USB encrypter service as";
            type = lib.types.str;
          };

          group = mkOption {
            default = "root";
            description = "The group to run the USB encrypter service as";
            type = lib.types.str;
          };

          partition-size-factors = mkOption {
            default = [ 0.33 0.33 0.33 ];
            description = "Factors of total partition size for the three partitions";
            type = lib.types.list lib.types.float;
          };

          output-json-file = mkOption {
            default = "/etc/usb-encrypter.json";
            description = "The file to output the USB encrypter configuration to";
            type = lib.types.str;
          };

          logfile = mkOption {
            default = "/var/log/usb-encrypter.log";
            description = "The file to output the USB encrypter logs to";
            type = lib.types.str;
          };

          hdd-info-file = mkOption {
            default = "/etc/usb-encrypter-hdd-info.json";
            description = "The file to output the USB encrypter HDD information to";
            type = lib.types.str;
          };

          mountpoint = mkOption {
            default = "/mnt/sensitive-data-hdd";
            description = "The mountpoint for the encrypted USB";
            type = lib.types.str;
          };

        };

        # if usb-encrypter service is enabled, add the poetryApp to the systemPackages
        config = lib.mkIf config.services.usb-encrypter.enable {
          environment.systemPackages = [ 
            poetryApp
            
            pkgs.parted
            pkgs.parted
            pkgs.cryptsetup
            pkgs.openssl
            pkgs.lsof
          ];
        };


      };

    };

  };


}
