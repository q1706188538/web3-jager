// 全局变量
let currentWallet = null;

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 创建钱包按钮
    document.getElementById('createWalletBtn').addEventListener('click', createWallet);
    
    // 导入钱包按钮
    document.getElementById('confirmImportBtn').addEventListener('click', importWallet);
    
    // 查询BNB余额按钮
    document.getElementById('checkBnbBalanceBtn').addEventListener('click', checkBnbBalance);
    
    // 查询代币余额按钮
    document.getElementById('checkTokenBalanceBtn').addEventListener('click', checkTokenBalance);
    
    // 转账BNB按钮
    document.getElementById('transferBnbBtn').addEventListener('click', transferBnb);
    
    // 转账代币按钮
    document.getElementById('transferTokenBtn').addEventListener('click', transferToken);
    
    // 调用合约按钮
    document.getElementById('callContractBtn').addEventListener('click', callContract);
});

// 复制到剪贴板
function copyToClipboard(elementId) {
    const text = document.getElementById(elementId).textContent;
    navigator.clipboard.writeText(text).then(() => {
        alert('已复制到剪贴板');
    }).catch(err => {
        console.error('复制失败:', err);
    });
}

// 创建新钱包
async function createWallet() {
    try {
        const useTestnet = document.getElementById('useTestnet').checked;
        
        const response = await fetch('/api/create-wallet', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ use_testnet: useTestnet })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentWallet = data.wallet;
            displayWalletInfo(data.wallet);
        } else {
            alert('创建钱包失败: ' + data.error);
        }
    } catch (error) {
        console.error('创建钱包出错:', error);
        alert('创建钱包出错: ' + error.message);
    }
}

// 导入钱包
async function importWallet() {
    try {
        const privateKey = document.getElementById('privateKeyInput').value.trim();
        const useTestnet = document.getElementById('useTestnet').checked;
        
        if (!privateKey) {
            alert('请输入私钥');
            return;
        }
        
        const response = await fetch('/api/import-wallet', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                private_key: privateKey,
                use_testnet: useTestnet
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentWallet = data.wallet;
            displayWalletInfo(data.wallet);
            
            // 关闭模态框
            const modal = bootstrap.Modal.getInstance(document.getElementById('importWalletModal'));
            modal.hide();
            
            // 清空输入框
            document.getElementById('privateKeyInput').value = '';
        } else {
            alert('导入钱包失败: ' + data.error);
        }
    } catch (error) {
        console.error('导入钱包出错:', error);
        alert('导入钱包出错: ' + error.message);
    }
}

// 显示钱包信息
function displayWalletInfo(wallet) {
    document.getElementById('walletAddress').textContent = wallet.address;
    document.getElementById('walletPrivateKey').textContent = wallet.private_key;
    document.getElementById('walletInfo').style.display = 'block';
}

// 查询BNB余额
async function checkBnbBalance() {
    try {
        const address = document.getElementById('bnbAddressInput').value.trim();
        const useTestnet = document.getElementById('useTestnet').checked;
        
        let url = '/api/get-bnb-balance';
        const params = new URLSearchParams();
        
        if (address) {
            params.append('address', address);
        } else if (!currentWallet) {
            alert('请输入地址或先创建/导入钱包');
            return;
        }
        
        params.append('use_testnet', useTestnet);
        url += '?' + params.toString();
        
        const response = await fetch(url);
        const data = await response.json();
        
        const resultElement = document.getElementById('bnbBalanceResult');
        
        if (data.success) {
            const balance = data.balance;
            resultElement.innerHTML = `
                <strong>地址:</strong> ${balance.address}<br>
                <strong>BNB余额:</strong> ${balance.balance_bnb}
            `;
            resultElement.style.display = 'block';
        } else {
            resultElement.innerHTML = `<strong>错误:</strong> ${data.error}`;
            resultElement.className = 'alert alert-danger mt-3';
            resultElement.style.display = 'block';
        }
    } catch (error) {
        console.error('查询BNB余额出错:', error);
        alert('查询BNB余额出错: ' + error.message);
    }
}

// 查询代币余额
async function checkTokenBalance() {
    try {
        const tokenAddress = document.getElementById('tokenAddressInput').value.trim();
        const address = document.getElementById('tokenWalletAddressInput').value.trim();
        const useTestnet = document.getElementById('useTestnet').checked;
        
        if (!tokenAddress) {
            alert('请输入代币合约地址');
            return;
        }
        
        let url = '/api/get-token-balance';
        const params = new URLSearchParams();
        
        params.append('token_address', tokenAddress);
        
        if (address) {
            params.append('address', address);
        } else if (!currentWallet) {
            alert('请输入地址或先创建/导入钱包');
            return;
        }
        
        params.append('use_testnet', useTestnet);
        url += '?' + params.toString();
        
        const response = await fetch(url);
        const data = await response.json();
        
        const resultElement = document.getElementById('tokenBalanceResult');
        
        if (data.success) {
            const balance = data.balance;
            resultElement.innerHTML = `
                <strong>地址:</strong> ${balance.address}<br>
                <strong>代币:</strong> ${balance.symbol}<br>
                <strong>余额:</strong> ${balance.balance_token}
            `;
            resultElement.className = 'alert alert-info mt-3';
            resultElement.style.display = 'block';
        } else {
            resultElement.innerHTML = `<strong>错误:</strong> ${data.error}`;
            resultElement.className = 'alert alert-danger mt-3';
            resultElement.style.display = 'block';
        }
    } catch (error) {
        console.error('查询代币余额出错:', error);
        alert('查询代币余额出错: ' + error.message);
    }
}

// 转账BNB
async function transferBnb() {
    try {
        if (!currentWallet) {
            alert('请先创建或导入钱包');
            return;
        }
        
        const toAddress = document.getElementById('bnbRecipientInput').value.trim();
        const amount = document.getElementById('bnbAmountInput').value;
        const gasPrice = document.getElementById('bnbGasPriceInput').value;
        
        if (!toAddress) {
            alert('请输入接收地址');
            return;
        }
        
        if (!amount || parseFloat(amount) <= 0) {
            alert('请输入有效的转账金额');
            return;
        }
        
        const requestData = {
            to_address: toAddress,
            amount: parseFloat(amount)
        };
        
        if (gasPrice && parseFloat(gasPrice) > 0) {
            requestData.gas_price = parseFloat(gasPrice);
        }
        
        const response = await fetch('/api/transfer-bnb', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        const resultElement = document.getElementById('bnbTransferResult');
        
        if (data.success) {
            const tx = data.transaction;
            resultElement.innerHTML = `
                <strong>交易已提交!</strong><br>
                <strong>交易哈希:</strong> ${tx.transaction_hash}<br>
                <strong>从:</strong> ${tx.from}<br>
                <strong>到:</strong> ${tx.to}<br>
                <strong>金额:</strong> ${tx.amount_bnb} BNB
            `;
            resultElement.className = 'alert alert-success mt-3';
            resultElement.style.display = 'block';
        } else {
            resultElement.innerHTML = `<strong>错误:</strong> ${data.error}`;
            resultElement.className = 'alert alert-danger mt-3';
            resultElement.style.display = 'block';
        }
    } catch (error) {
        console.error('转账BNB出错:', error);
        alert('转账BNB出错: ' + error.message);
    }
}

// 转账代币
async function transferToken() {
    try {
        if (!currentWallet) {
            alert('请先创建或导入钱包');
            return;
        }
        
        const tokenAddress = document.getElementById('tokenContractInput').value.trim();
        const toAddress = document.getElementById('tokenRecipientInput').value.trim();
        const amount = document.getElementById('tokenAmountInput').value;
        const gasPrice = document.getElementById('tokenGasPriceInput').value;
        
        if (!tokenAddress) {
            alert('请输入代币合约地址');
            return;
        }
        
        if (!toAddress) {
            alert('请输入接收地址');
            return;
        }
        
        if (!amount || parseFloat(amount) <= 0) {
            alert('请输入有效的转账金额');
            return;
        }
        
        const requestData = {
            token_address: tokenAddress,
            to_address: toAddress,
            amount: parseFloat(amount)
        };
        
        if (gasPrice && parseFloat(gasPrice) > 0) {
            requestData.gas_price = parseFloat(gasPrice);
        }
        
        const response = await fetch('/api/transfer-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        const resultElement = document.getElementById('tokenTransferResult');
        
        if (data.success) {
            const tx = data.transaction;
            resultElement.innerHTML = `
                <strong>交易已提交!</strong><br>
                <strong>交易哈希:</strong> ${tx.transaction_hash}<br>
                <strong>从:</strong> ${tx.from}<br>
                <strong>到:</strong> ${tx.to}<br>
                <strong>代币地址:</strong> ${tx.token_address}<br>
                <strong>金额:</strong> ${tx.amount}
            `;
            resultElement.className = 'alert alert-success mt-3';
            resultElement.style.display = 'block';
        } else {
            resultElement.innerHTML = `<strong>错误:</strong> ${data.error}`;
            resultElement.className = 'alert alert-danger mt-3';
            resultElement.style.display = 'block';
        }
    } catch (error) {
        console.error('转账代币出错:', error);
        alert('转账代币出错: ' + error.message);
    }
}

// 调用合约
async function callContract() {
    try {
        if (!currentWallet) {
            alert('请先创建或导入钱包');
            return;
        }
        
        const contractAddress = document.getElementById('contractAddressInput').value.trim();
        const contractAbi = document.getElementById('contractAbiInput').value.trim();
        const functionName = document.getElementById('contractFunctionInput').value.trim();
        const argsInput = document.getElementById('contractArgsInput').value.trim();
        const valueInput = document.getElementById('contractValueInput').value;
        
        if (!contractAddress) {
            alert('请输入合约地址');
            return;
        }
        
        if (!contractAbi) {
            alert('请输入合约ABI');
            return;
        }
        
        if (!functionName) {
            alert('请输入函数名称');
            return;
        }
        
        let functionArgs = [];
        if (argsInput) {
            try {
                functionArgs = JSON.parse(argsInput);
                if (!Array.isArray(functionArgs)) {
                    functionArgs = [functionArgs];
                }
            } catch (e) {
                alert('函数参数格式无效，请使用JSON数组格式');
                return;
            }
        }
        
        const requestData = {
            contract_address: contractAddress,
            contract_abi: JSON.parse(contractAbi),
            function_name: functionName,
            function_args: functionArgs
        };
        
        if (valueInput && parseFloat(valueInput) > 0) {
            requestData.value = parseFloat(valueInput);
        }
        
        const response = await fetch('/api/interact-with-contract', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        const resultElement = document.getElementById('contractResult');
        
        if (data.success) {
            const result = data.result;
            
            if (result.type === 'read') {
                resultElement.innerHTML = `
                    <strong>调用成功!</strong><br>
                    <strong>结果:</strong> ${JSON.stringify(result.result)}
                `;
            } else {
                resultElement.innerHTML = `
                    <strong>交易已提交!</strong><br>
                    <strong>交易哈希:</strong> ${result.transaction_hash}<br>
                    <strong>从:</strong> ${result.from}<br>
                    <strong>到:</strong> ${result.to}<br>
                    <strong>函数:</strong> ${result.function}
                `;
            }
            
            resultElement.className = 'alert alert-success mt-3';
            resultElement.style.display = 'block';
        } else {
            resultElement.innerHTML = `<strong>错误:</strong> ${data.error}`;
            resultElement.className = 'alert alert-danger mt-3';
            resultElement.style.display = 'block';
        }
    } catch (error) {
        console.error('调用合约出错:', error);
        alert('调用合约出错: ' + error.message);
    }
}
