const { ethers } = require("hardhat");

async function main() {
  const [deployer] = await ethers.getSigners();

  console.log("Deploying BaselineStorage contract with the account:", deployer.address);
  console.log("Account balance:", (await deployer.provider.getBalance(deployer.address)).toString());

  const BaselineStorage = await ethers.getContractFactory("BaselineStorage");
  const baselineStorage = await BaselineStorage.deploy();

  await baselineStorage.waitForDeployment();

  console.log("BaselineStorage deployed to:", await baselineStorage.getAddress());
  
  // Save the address for the service
  console.log("\n=== UPDATE BASELINE SERVICE ===");
  console.log(`Update baseline_service.py with this address:`);
  console.log(`self.baseline_contract_address = "${await baselineStorage.getAddress()}"`);
  console.log("================================\n");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });